// v0.999.51 D1 the kit: Trust / registrations (real only) - her registration numbers set out like a register, her
// awards and years beside the facts, or the promises she keeps with the payment modes she takes. Nothing invented:
// every number and award comes from her.
import * as React from "react";
import { Award, BadgeCheck, Check, Copy, CreditCard, ShieldCheck } from "lucide-react";
import { Section, Container, SectionHead, type Tone } from "./_kit";
import { toast } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";

export const variants = ["registry", "badges", "promises"] as const;
export type CertificatesTrustVariant = (typeof variants)[number];

export interface Registration {
  label: string;
  number: string;
  issuer?: string;
  validTill?: string;
}

export interface TrustFact {
  value: string;
  label: string;
}

export interface TrustAward {
  title: string;
  by?: string;
  year?: string;
}

export interface TrustPromise {
  title: string;
  detail?: string;
}

export interface CertificatesTrustProps {
  variant?: CertificatesTrustVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  registrations?: Registration[];
  facts?: TrustFact[];
  awards?: TrustAward[];
  promises?: TrustPromise[];
  payments?: string[];
  note?: string;
}

export const sample: Required<Omit<CertificatesTrustProps, "variant" | "tone">> = {
  title: "Registered, licensed and on record",
  intro: "The numbers below are ours to quote. Ask for a copy of any certificate before you place an order.",
  registrations: [
    { label: "GSTIN", number: "27ABCDE1234F1Z5", issuer: "Goods and Services Tax, Maharashtra" },
    { label: "FSSAI licence", number: "11500000000000", issuer: "Food Safety and Standards Authority of India", validTill: "Mar 2028" },
    { label: "Udyam registration", number: "UDYAM-MH-26-0000000", issuer: "Ministry of MSME" },
    { label: "Shop and establishment", number: "PMC/SE/2019/000000", issuer: "Pune Municipal Corporation" },
  ],
  facts: [
    { value: "Since 2009", label: "cooking for weddings and offices" },
    { value: "1,800+", label: "events served in Pune and Mumbai" },
    { value: "4.7 / 5", label: "average from 420 Google reviews" },
  ],
  awards: [
    { title: "Best caterer, small events", by: "Pune Wedding Planners' Forum", year: "2024" },
    { title: "Kitchen hygiene rating: 5", by: "FSSAI Hygiene Rating Scheme", year: "2025" },
    { title: "Member", by: "Maharashtra Caterers' Association" },
  ],
  promises: [
    { title: "Food cooked on the day", detail: "Nothing is cooked the night before. The kitchen starts at 5 am for lunch events." },
    { title: "Staff with health cards", detail: "Every cook and server has a current medical certificate, renewed each year." },
    { title: "Written menu and rate", detail: "You get the menu, per-plate rate and taxes in writing before you pay an advance." },
    { title: "Advance back if we cancel", detail: "If we cannot serve your date for any reason, the full advance is returned within 7 days." },
  ],
  payments: ["UPI", "Debit and credit cards", "Net banking", "Cheque", "Cash"],
  note: "Sample details - replace with your own registration numbers before going live.",
};

function soft(tone?: Tone) {
  return tone === "primary" || tone === "ink" ? "opacity-75" : "text-muted";
}

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function CopyNumber({ value, label }: { value: string; label: string }) {
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
    <button
      type="button"
      onClick={copy}
      aria-label={`Copy ${label}`}
      className="inline-flex size-10 shrink-0 items-center justify-center rounded-control text-muted transition-colors hover:bg-ink/5 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
    >
      {done ? <Check className="size-4 text-ok" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
    </button>
  );
}

export default function CertificatesTrust({ variant = "registry", tone, ...rest }: CertificatesTrustProps) {
  const p = { ...sample, ...given(rest) };
  const muted = soft(tone);

  if (variant === "badges") {
    return (
      <Section block="certificates_trust" variant={variant} tone={tone ?? "surface"} className="[&_h2]:text-inherit">
        <Container>
          <SectionHead title={p.title} intro={p.intro} align="center" />
          <dl className="mx-auto grid max-w-4xl gap-8 text-center sm:grid-cols-3">
            {p.facts.map((f) => (
              <div key={f.label} className="flex flex-col gap-1">
                <dt className={cn("order-2 text-sm", muted)}>{f.label}</dt>
                <dd className="order-1 font-head text-4xl font-semibold tracking-tight">{f.value}</dd>
              </div>
            ))}
          </dl>
          <ul className="mx-auto mt-14 flex max-w-5xl flex-wrap justify-center gap-3">
            {p.awards.map((a) => (
              <li key={a.title + (a.by ?? "")} className="flex min-w-0 items-center gap-3 rounded-full border border-line bg-bg py-2 pl-3 pr-5 text-ink">
                <Award className="size-5 shrink-0 text-primary" aria-hidden="true" />
                <span className="flex min-w-0 flex-col leading-tight">
                  <span className="text-sm font-semibold break-words">{a.title}</span>
                  <span className="text-xs text-muted break-words">{[a.by, a.year].filter(Boolean).join(", ")}</span>
                </span>
              </li>
            ))}
          </ul>
          <ul className={cn("mx-auto mt-10 flex max-w-3xl flex-wrap justify-center gap-x-6 gap-y-2 text-sm", muted)}>
            {p.registrations.map((r) => (
              <li key={r.label} className="min-w-0 break-all">
                <span className="font-medium">{r.label}</span> {r.number}
              </li>
            ))}
          </ul>
          {p.note ? <p className={cn("mt-4 text-center text-xs", muted)}>{p.note}</p> : null}
        </Container>
      </Section>
    );
  }

  if (variant === "promises") {
    return (
      <Section block="certificates_trust" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
        <Container>
          <div className="grid gap-12 lg:grid-cols-12">
            <div className="lg:col-span-4">
              <SectionHead title={p.title} intro={p.intro} className="mb-8 sm:mb-8" />
              <div className="flex flex-col gap-3">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <CreditCard className="size-4" aria-hidden="true" /> Ways to pay
                </p>
                <ul className="flex flex-wrap gap-2">
                  {p.payments.map((m) => (
                    <li key={m} className="rounded-control border border-line px-3 py-1.5 text-sm">
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <ol className="grid min-w-0 gap-x-10 gap-y-8 sm:grid-cols-2 lg:col-span-8">
              {p.promises.map((pr) => (
                <li key={pr.title} className="flex gap-4">
                  <ShieldCheck className="mt-1 size-5 shrink-0 text-ok" aria-hidden="true" />
                  <div className="flex min-w-0 flex-col gap-1.5">
                    <h3 className="font-head text-lg font-semibold text-inherit">{pr.title}</h3>
                    {pr.detail ? <p className={cn("text-sm leading-relaxed", muted)}>{pr.detail}</p> : null}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="certificates_trust" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
      <Container>
        <div className="grid gap-10 lg:grid-cols-12 lg:gap-14">
          <div className="lg:col-span-5">
            <SectionHead title={p.title} intro={p.intro} className="mb-6 sm:mb-6" />
            <ul className="flex flex-col gap-2">
              {p.awards.map((a) => (
                <li key={a.title + (a.by ?? "")} className="flex gap-2 text-sm">
                  <BadgeCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                  <span className="min-w-0">
                    <span className="font-medium">{a.title}</span>
                    {a.by ? <span className={muted}> - {a.by}</span> : null}
                    {a.year ? <span className={muted}>, {a.year}</span> : null}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div className="min-w-0 lg:col-span-7">
            <dl className="divide-y divide-line overflow-hidden rounded-card border border-line bg-surface text-ink shadow-card">
              {p.registrations.map((r) => (
                <div key={r.label} className="flex items-center gap-3 px-5 py-4">
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <dt className="text-xs font-medium text-muted">{r.label}</dt>
                    <dd className="font-head text-lg font-semibold tracking-wide break-all">{r.number}</dd>
                    {r.issuer || r.validTill ? (
                      <dd className="text-xs text-muted">
                        {[r.issuer, r.validTill ? `valid till ${r.validTill}` : ""].filter(Boolean).join(" · ")}
                      </dd>
                    ) : null}
                  </div>
                  <CopyNumber value={r.number} label={r.label} />
                </div>
              ))}
            </dl>
            {p.note ? <p className={cn("mt-4 text-xs", muted)}>{p.note}</p> : null}
          </div>
        </div>
      </Container>
    </Section>
  );
}
