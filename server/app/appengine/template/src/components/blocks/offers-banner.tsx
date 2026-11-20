"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 the kit: Offers - a thin strip above the page, coupon cards with a code to copy, or a festival band
// that counts down to the offer's last day. Only her offers, her prices and her end dates.
import * as React from "react";
import { ArrowRight, Check, Copy, Tag, X } from "lucide-react";
import { Section, Container, SectionHead, rupees, type Tone } from "./_kit";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";

export const variants = ["strip", "coupons", "countdown"] as const;
export type OffersBannerVariant = (typeof variants)[number];

export interface Offer {
  title: string;
  detail?: string;
  /** a code she gives customers to quote at the counter or at checkout */
  code?: string;
  price?: number;
  was?: number;
  /** a plain end line, e.g. "Till 31 Dec" */
  ends?: string;
}

export interface OffersBannerProps {
  variant?: OffersBannerVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  offers?: Offer[];
  /** ISO date-time the offer ends (the countdown counts to it) */
  endsAt?: string;
  terms?: string;
  action?: { label: string; href: string };
  dismissible?: boolean;
}

const inDays = new Date(Date.now() + (4 * 24 + 7) * 3600 * 1000).toISOString();

export const sample: Required<Omit<OffersBannerProps, "variant" | "tone">> = {
  title: "Diwali week at the shop",
  intro: "Gift boxes packed the same day. Order by phone or walk in - Shivaji Nagar, Pune.",
  offers: [
    {
      title: "Dry fruit gift box, 500 g",
      detail: "Kaju, badam, pista and anjeer in a wooden box with your note inside.",
      price: 899,
      was: 1099,
      code: "DIWALI200",
      ends: "Till Sunday",
    },
    {
      title: "Office orders of 25 boxes or more",
      detail: "Your company's card printed on every box, delivered anywhere in Pune.",
      code: "TEAM10",
      ends: "Orders by 30 Oct",
    },
    {
      title: "First order on WhatsApp",
      detail: "Free delivery within 5 km on your first order, any amount.",
      code: "FIRSTFREE",
      ends: "All month",
    },
  ],
  endsAt: inDays,
  terms: "One code per order. Prices include GST. Codes are not added to sale items.",
  action: { label: "Order now", href: "#contact" },
  dismissible: true,
};

const NOTCH: Record<Tone, string> = { plain: "bg-bg", surface: "bg-surface", primary: "bg-primary", ink: "bg-ink" };

function soft(tone?: Tone) {
  return tone === "primary" || tone === "ink" ? "opacity-75" : "text-muted";
}

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function useLeft(endsAt: string, on: boolean) {
  const end = React.useMemo(() => new Date(endsAt).getTime(), [endsAt]);
  const [now, setNow] = React.useState(() => Date.now());
  React.useEffect(() => {
    if (!on || !Number.isFinite(end)) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [end, on]);
  if (!Number.isFinite(end)) return null;
  const ms = Math.max(0, end - now);
  const s = Math.floor(ms / 1000);
  return { over: ms === 0, days: Math.floor(s / 86400), hours: Math.floor((s % 86400) / 3600), mins: Math.floor((s % 3600) / 60), secs: s % 60 };
}

function CopyCode({ code, className }: { code: string; className?: string }) {
  const [done, setDone] = React.useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setDone(true);
      toast.success(`Code ${code} copied`);
      setTimeout(() => setDone(false), 2000);
    } catch {
      toast(`Your code is ${code}`);
    }
  };
  return (
    <button
      type="button"
      onClick={copy}
      aria-label={`Copy code ${code}`}
      className={cn(
        "inline-flex h-10 items-center gap-2 rounded-control border border-dashed border-current px-3 font-head text-sm font-semibold tracking-wide transition-colors hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
        className,
      )}
    >
      {code}
      {done ? <Check className="size-4" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
    </button>
  );
}

function PriceLine({ o }: { o: Offer }) {
  if (o.price === undefined) return null;
  return (
    <p className="flex items-baseline gap-2">
      <span className="font-head text-2xl font-semibold">{rupees(o.price)}</span>
      {o.was !== undefined && o.was > o.price ? (
        <>
          <span className="text-sm text-muted line-through">{rupees(o.was)}</span>
          <span className="text-sm font-medium text-ok">Save {rupees(o.was - o.price)}</span>
        </>
      ) : null}
    </p>
  );
}

export default function OffersBanner({ variant = "strip", tone, ...rest }: OffersBannerProps) {
  const p = { ...sample, ...given(rest) };
  const muted = soft(tone);
  const [hidden, setHidden] = React.useState(false);
  const left = useLeft(p.endsAt, variant === "countdown");
  const lead = p.offers[0];

  if (variant === "strip") {
    if (hidden || !lead) return null;
    return (
      <Section block="offers_banner" variant={variant} tone={tone ?? "primary"} className="py-0 sm:py-0">
        <Container wide className="flex min-h-12 items-center gap-3 py-2 text-sm">
          <Tag className="hidden size-4 shrink-0 sm:block" aria-hidden="true" />
          <p className="min-w-0 flex-1 break-words">
            <span className="font-semibold">{lead.title}</span>
            {lead.price !== undefined ? <span> at {rupees(lead.price)}</span> : null}
            {lead.code ? (
              <span>
                {" "}- use code <span className="font-semibold tracking-wide">{lead.code}</span>
              </span>
            ) : null}
            {lead.ends ? <span className="opacity-80"> · {lead.ends}</span> : null}
          </p>
          <a
            href={p.action.href}
            className="inline-flex h-10 shrink-0 items-center gap-1 rounded-control px-2 font-medium text-inherit underline underline-offset-4 hover:no-underline"
          >
            {p.action.label}
            <ArrowRight className="size-4" aria-hidden="true" />
          </a>
          {p.dismissible ? (
            <button
              type="button"
              onClick={() => setHidden(true)}
              aria-label="Hide this offer"
              className="inline-flex size-10 shrink-0 items-center justify-center rounded-control transition-colors hover:bg-ink/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-current"
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          ) : null}
        </Container>
      </Section>
    );
  }

  if (variant === "countdown") {
    const units = left ? ([["days", left.days], ["hours", left.hours], ["mins", left.mins], ["secs", left.secs]] as const) : [];
    return (
      <Section block="offers_banner" variant={variant} tone={tone ?? "ink"} className="overflow-hidden [&_h2]:text-inherit">
        <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-24 size-96 rounded-full bg-primary/25" />
        <div aria-hidden="true" className="pointer-events-none absolute -bottom-32 left-1/3 size-72 rounded-full bg-accent/15" />
        <Container className="relative grid items-center gap-10 lg:grid-cols-12">
          <div className="flex min-w-0 flex-col gap-5 lg:col-span-7">
            <h2 className="font-head text-4xl font-semibold tracking-tight text-inherit sm:text-6xl">{p.title}</h2>
            <p className={cn("max-w-xl text-lg", muted)}>{p.intro}</p>
            {left ? (
              left.over ? (
                <p className="font-medium">This offer has ended. Ask us about the next one.</p>
              ) : (
                <div role="timer" aria-label={`Offer ends in ${left.days} days and ${left.hours} hours`} className="flex flex-wrap gap-3">
                  {units.map(([u, v]) => (
                    <div key={u} className="flex w-20 flex-col items-center rounded-control border border-current/20 px-2 py-3">
                      <span className="font-head text-3xl font-semibold tabular-nums">{String(v).padStart(2, "0")}</span>
                      <span className={cn("text-xs", muted)}>{u}</span>
                    </div>
                  ))}
                </div>
              )
            ) : null}
            <div className="flex flex-wrap gap-3 pt-2">
              <Button size="lg" variant="accent" asChild>
                <a href={p.action.href}>{p.action.label}</a>
              </Button>
            </div>
            {p.terms ? <p className={cn("text-xs", muted)}>{p.terms}</p> : null}
          </div>
          <ul className="flex min-w-0 flex-col gap-3 lg:col-span-5">
            {p.offers.map((o) => (
              <li key={o.title} className="rounded-card bg-surface p-5 text-ink shadow-card">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-head text-base font-semibold break-words">{o.title}</h3>
                  {o.ends ? <Badge tone="neutral">{o.ends}</Badge> : null}
                </div>
                {o.detail ? <p className="mt-1 text-sm text-muted">{o.detail}</p> : null}
                <div className="mt-3">
                  <PriceLine o={o} />
                </div>
              </li>
            ))}
          </ul>
        </Container>
      </Section>
    );
  }

  const notch = NOTCH[tone ?? "plain"];
  return (
    <Section block="offers_banner" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <ul className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {p.offers.map((o) => (
            <li key={o.title} className="relative flex min-w-0 flex-col rounded-card border border-line bg-surface text-ink shadow-card">
              <div className="flex flex-1 flex-col gap-3 p-6">
                {o.ends ? <p className="text-xs font-medium text-muted">{o.ends}</p> : null}
                <h3 className="font-head text-lg font-semibold break-words">{o.title}</h3>
                {o.detail ? <p className="text-sm text-muted">{o.detail}</p> : null}
                <PriceLine o={o} />
              </div>
              <div className="relative border-t border-dashed border-line px-6 py-4">
                <span aria-hidden="true" className={cn("absolute -left-3 -top-3 size-6 rounded-full border-r border-line", notch)} />
                <span aria-hidden="true" className={cn("absolute -right-3 -top-3 size-6 rounded-full border-l border-line", notch)} />
                {o.code ? (
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs text-muted">Tap to copy</span>
                    <CopyCode code={o.code} className="text-primary" />
                  </div>
                ) : (
                  <a href={p.action.href} className="inline-flex h-10 items-center gap-1 text-sm font-medium">
                    {p.action.label} <ArrowRight className="size-4" aria-hidden="true" />
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
        {p.terms ? <p className={cn("mt-6 text-xs", muted)}>{p.terms}</p> : null}
      </Container>
    </Section>
  );
}
