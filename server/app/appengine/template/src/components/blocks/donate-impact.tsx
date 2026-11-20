// v0.999.51 D1 the kit: Donate / impact - what a gift does with her real numbers and a choice of amount, the list
// of what a project still needs, or every way to give (UPI, bank, 80G note only when she has one). Money moves only
// in the giver's own UPI app or bank, by their own tap.
import * as React from "react";
import { ArrowRight, Check, Copy, HandHeart, Landmark, Smartphone } from "lucide-react";
import { Section, Container, SectionHead, Picture, rupees, type Tone } from "./_kit";
import { NumberTicker } from "@/components/effects";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";

export const variants = ["impact", "needs", "give"] as const;
export type DonateImpactVariant = (typeof variants)[number];

export interface ImpactStat {
  value: number;
  label: string;
  suffix?: string;
}

export interface GiveAmount {
  value: number;
  /** what this amount does, in her words */
  does: string;
}

export interface Need {
  item: string;
  /** how many are needed in all, and how many are already given */
  need: number;
  have: number;
  unit?: string;
  /** rupees for one, if she gives it */
  cost?: number;
}

export interface DonateImpactProps {
  variant?: DonateImpactVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  stats?: ImpactStat[];
  amounts?: GiveAmount[];
  needs?: Need[];
  needsTitle?: string;
  upi?: { id: string; name: string };
  bank?: { name: string; account: string; ifsc: string; bank: string; branch?: string };
  /** her 80G line, only when she has the registration */
  note80g?: string;
  image?: string;
  action?: { label: string; href: string };
}

export const sample: Required<Omit<DonateImpactProps, "variant" | "tone">> = {
  title: "A hot lunch for every child in class",
  intro: "We cook and serve lunch in six municipal schools in Pune's Yerawada ward, every school day since 2017.",
  stats: [
    { value: 1240, label: "children fed each school day" },
    { value: 6, label: "schools in Yerawada ward" },
    { value: 9, suffix: " yrs", label: "without a missed day" },
  ],
  amounts: [
    { value: 500, does: "Lunch for one child for a month" },
    { value: 1500, does: "A month's dal and rice for one classroom" },
    { value: 6000, does: "A year of lunches for one child" },
  ],
  needsTitle: "What we still need this term",
  needs: [
    { item: "Steel lunch plates", need: 400, have: 260, unit: "plates", cost: 180 },
    { item: "Large cooking vessels", need: 12, have: 5, unit: "vessels", cost: 4200 },
    { item: "Monthly gas cylinders", need: 30, have: 22, unit: "cylinders", cost: 1100 },
    { item: "Volunteers for Saturday serving", need: 20, have: 14, unit: "people" },
  ],
  upi: { id: "annapurnatrust@upi", name: "Annapurna Seva Trust" },
  bank: { name: "Annapurna Seva Trust", account: "000123456789", ifsc: "ABCD0001234", bank: "Sample Bank", branch: "Yerawada, Pune" },
  note80g: "Gifts are eligible for tax deduction under section 80G. We email the receipt within 7 days.",
  image: "",
  action: { label: "Volunteer with us", href: "#contact" },
};

function soft(tone?: Tone) {
  return tone === "primary" || tone === "ink" ? "opacity-75" : "text-muted";
}

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function upiLink(upi: { id: string; name: string }, amount?: number) {
  const q = new URLSearchParams({ pa: upi.id, pn: upi.name, cu: "INR", tn: "Donation" });
  if (amount) q.set("am", String(amount));
  return `upi://pay?${q.toString()}`;
}

function CopyRow({ label, value }: { label: string; value: string }) {
  const [done, setDone] = React.useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setDone(true);
      toast.success(`${label} copied`);
      setTimeout(() => setDone(false), 2000);
    } catch {
      toast(`${label}: ${value}`);
    }
  };
  return (
    <div className="flex items-center gap-3 py-3">
      <div className="flex min-w-0 flex-1 flex-col">
        <dt className="text-xs text-muted">{label}</dt>
        <dd className="font-medium break-all">{value}</dd>
      </div>
      <button
        type="button"
        onClick={copy}
        aria-label={`Copy ${label}`}
        className="inline-flex size-10 shrink-0 items-center justify-center rounded-control text-muted transition-colors hover:bg-ink/5 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      >
        {done ? <Check className="size-4 text-ok" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
      </button>
    </div>
  );
}

export default function DonateImpact({ variant = "impact", tone, ...rest }: DonateImpactProps) {
  const p = { ...sample, ...given(rest) };
  const muted = soft(tone);
  const [pick, setPick] = React.useState(1);
  const chosen = p.amounts[pick] ?? p.amounts[0];

  if (variant === "needs") {
    return (
      <Section block="donate_impact" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
        <Container>
          <div className="grid gap-12 lg:grid-cols-12">
            <div className="flex flex-col gap-6 lg:col-span-5">
              <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
              <Picture src={p.image || undefined} alt="Lunch being served in a school" label={p.upi.name} ratio="4/3" />
            </div>
            <div className="flex min-w-0 flex-col gap-6 lg:col-span-7">
              <h3 className="font-head text-xl font-semibold text-inherit">{p.needsTitle}</h3>
              <ul className="flex flex-col divide-y divide-line border-y border-line">
                {p.needs.map((n) => {
                  const pct = n.need > 0 ? Math.min(100, Math.round((n.have / n.need) * 100)) : 0;
                  const left = Math.max(0, n.need - n.have);
                  return (
                    <li key={n.item} className="flex flex-col gap-3 py-5">
                      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                        <span className="font-medium break-words">{n.item}</span>
                        <span className={cn("text-sm tabular-nums", muted)}>
                          {n.have} of {n.need} {n.unit ?? ""}
                        </span>
                      </div>
                      <div
                        role="progressbar"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={pct}
                        aria-label={`${n.item}: ${pct}% given`}
                        className="h-2 overflow-hidden rounded-full bg-ink/10"
                      >
                        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                      </div>
                      <p className={cn("text-sm", muted)}>
                        {left > 0 ? `${left} ${n.unit ?? ""} still needed` : "Fully given - thank you"}
                        {n.cost && left > 0 ? ` · ${rupees(n.cost)} each` : ""}
                      </p>
                    </li>
                  );
                })}
              </ul>
              <div className="flex flex-wrap gap-3">
                <Button asChild size="lg">
                  <a href={upiLink(p.upi)}>
                    <HandHeart className="size-5" aria-hidden="true" /> Give by UPI
                  </a>
                </Button>
                <Button asChild size="lg" variant="outline" className="border-current/25 text-inherit hover:bg-current/5">
                  <a href={p.action.href}>{p.action.label}</a>
                </Button>
              </div>
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "give") {
    return (
      <Section block="donate_impact" variant={variant} tone={tone ?? "surface"} className="[&_h2]:text-inherit">
        <Container>
          <SectionHead title={p.title} intro={p.intro} />
          <div className="grid gap-6 md:grid-cols-2">
            <div className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-bg p-6 text-ink">
              <h3 className="flex items-center gap-2 font-head text-lg font-semibold">
                <Smartphone className="size-5 text-primary" aria-hidden="true" /> UPI
              </h3>
              <p className="text-sm text-muted">Pay from any UPI app. On a phone, the button opens your app with our details filled in.</p>
              <dl className="divide-y divide-line border-y border-line">
                <CopyRow label="UPI ID" value={p.upi.id} />
                <CopyRow label="Name" value={p.upi.name} />
              </dl>
              <Button asChild className="mt-auto self-start">
                <a href={upiLink(p.upi)}>Open UPI app</a>
              </Button>
            </div>
            <div className="flex min-w-0 flex-col gap-4 rounded-card border border-line bg-bg p-6 text-ink">
              <h3 className="flex items-center gap-2 font-head text-lg font-semibold">
                <Landmark className="size-5 text-primary" aria-hidden="true" /> Bank transfer
              </h3>
              <p className="text-sm text-muted">NEFT, RTGS or IMPS. Send us the reference number and we will email the receipt.</p>
              <dl className="divide-y divide-line border-y border-line">
                <CopyRow label="Account name" value={p.bank.name} />
                <CopyRow label="Account number" value={p.bank.account} />
                <CopyRow label="IFSC" value={p.bank.ifsc} />
                <div className="py-3">
                  <dt className="text-xs text-muted">Bank</dt>
                  <dd className="font-medium">{[p.bank.bank, p.bank.branch].filter(Boolean).join(", ")}</dd>
                </div>
              </dl>
            </div>
          </div>
          {p.note80g ? (
            <p className="mt-6 flex gap-3 rounded-card bg-primary/10 p-4 text-sm">
              <Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
              <span className="min-w-0">{p.note80g}</span>
            </p>
          ) : null}
        </Container>
      </Section>
    );
  }

  return (
    <Section block="donate_impact" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
      <Container>
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="flex min-w-0 flex-col gap-8 lg:col-span-7">
            <h2 className="font-head text-4xl font-semibold tracking-tight text-inherit sm:text-5xl">{p.title}</h2>
            <p className={cn("max-w-xl text-lg", muted)}>{p.intro}</p>
            <dl className="grid grid-cols-1 gap-6 border-t border-line pt-8 sm:grid-cols-3">
              {p.stats.map((s) => (
                <div key={s.label} className="flex flex-col gap-1">
                  <dt className={cn("order-2 text-sm", muted)}>{s.label}</dt>
                  <dd className="order-1 font-head text-4xl font-semibold tracking-tight">
                    <NumberTicker value={s.value} suffix={s.suffix} />
                  </dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="min-w-0 rounded-card border border-line bg-surface p-6 text-ink shadow-card sm:p-8 lg:col-span-5">
            <h3 className="font-head text-xl font-semibold">Choose an amount</h3>
            <div role="radiogroup" aria-label="Amount to give" className="mt-5 flex flex-col gap-2">
              {p.amounts.map((a, i) => {
                const on = i === pick;
                return (
                  <button
                    key={a.value}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    onClick={() => setPick(i)}
                    className={cn(
                      "flex min-h-14 items-center gap-4 rounded-control border px-4 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                      on ? "border-primary bg-primary/10" : "border-line hover:border-ink/40",
                    )}
                  >
                    <span
                      aria-hidden="true"
                      className={cn("flex size-5 shrink-0 items-center justify-center rounded-full border-2", on ? "border-primary" : "border-line")}
                    >
                      {on ? <span className="size-2.5 rounded-full bg-primary" /> : null}
                    </span>
                    <span className="font-head text-lg font-semibold tabular-nums">{rupees(a.value)}</span>
                    <span className="min-w-0 text-sm text-muted">{a.does}</span>
                  </button>
                );
              })}
            </div>
            {chosen ? (
              <Button asChild size="lg" className="mt-6 w-full">
                <a href={upiLink(p.upi, chosen.value)}>
                  Give {rupees(chosen.value)} by UPI <ArrowRight className="size-4" aria-hidden="true" />
                </a>
              </Button>
            ) : null}
            <p className="mt-3 text-xs text-muted">
              Opens your UPI app with {p.upi.id}. {p.note80g ? "80G receipt by email." : ""}
            </p>
          </div>
        </div>
      </Container>
    </Section>
  );
}
