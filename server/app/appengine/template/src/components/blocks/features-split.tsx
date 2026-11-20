// v0.999.51 D1 block: Feature rows. Three layouts - picture / words rows that swap sides, a list of features on one
// side that changes the picture on the other, and one big picture beside a checklist and a single number.
import * as React from "react";
import { ArrowRight, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { NumberTicker } from "@/components/effects";
import { Section, Container, SectionHead, Picture, type Tone } from "./_kit";

export const variants = ["alternating", "switcher", "checklist"] as const;
export type FeaturesSplitVariant = (typeof variants)[number];

export interface Feature {
  title: string;
  text: string;
  points?: string[];
  photo?: string;
  label?: string;
}

export interface FeaturesSplitProps {
  variant?: FeaturesSplitVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  features?: Feature[];
  checklist?: string[];
  stat?: { value: number; suffix?: string; label: string };
  photo?: string;
  action?: { label: string; href: string };
}

export const sample: Required<Omit<FeaturesSplitProps, "variant" | "tone">> = {
  title: "What you get when you come to us",
  intro: "Three things we do the same way every time, so you always know what to expect.",
  features: [
    {
      title: "A clear plan before any work starts",
      text: "We listen first, then write down what will be done, how long it takes and what it costs. Nothing is added later without asking you.",
      points: ["Written estimate on WhatsApp", "No charge for the first discussion"],
      label: "Planning on paper",
    },
    {
      title: "Done on the day we promise",
      text: "Our calendar has breathing room built in, so a busy afternoon never pushes your work to next week.",
      points: ["Reminder the evening before", "A message the moment it is ready"],
      label: "The finished work",
    },
    {
      title: "Someone to call afterwards",
      text: "You get the number of the person who did the work. If anything is not right within thirty days, we fix it at no cost.",
      points: ["30-day free fix", "Same person, every time"],
      label: "A follow-up call",
    },
  ],
  checklist: [
    "Prices written down before we begin",
    "GST bill for every payment",
    "UPI, cards and cash accepted",
    "Open six days a week, 10 am to 8 pm",
    "Free fix within thirty days",
  ],
  stat: { value: 4200, suffix: "+", label: "jobs finished in Nashik since 2016" },
  photo: "",
  action: { label: "See what it costs", href: "#pricing" },
};

export default function FeaturesSplit({ variant = "alternating", tone, ...rest }: FeaturesSplitProps) {
  const d = { ...sample, ...rest };
  const [active, setActive] = React.useState(0);
  const pictureId = React.useId();

  if (variant === "switcher") {
    const f = d.features[Math.min(active, d.features.length - 1)];
    return (
      <Section block="features_split" variant={variant} tone={tone ?? "surface"}>
        <Container>
          <SectionHead title={d.title} intro={d.intro} />
          <div className="grid gap-10 lg:grid-cols-12 lg:gap-16">
            <div role="group" aria-label="Features" className="flex flex-col lg:col-span-5">
              {d.features.map((x, i) => {
                const on = i === active;
                return (
                  <button
                    key={x.title}
                    type="button"
                    aria-pressed={on}
                    aria-controls={pictureId}
                    onClick={() => setActive(i)}
                    className={cn(
                      "relative border-l-2 py-5 pl-6 pr-2 text-left transition-colors",
                      on ? "border-primary" : "border-line hover:border-ink/30",
                    )}
                  >
                    <span className={cn("block text-lg font-semibold transition-colors", on ? "text-ink" : "text-muted")}>{x.title}</span>
                    {on ? <span className="mt-2 block animate-fade-in leading-relaxed text-muted">{x.text}</span> : null}
                  </button>
                );
              })}
            </div>
            {f ? (
              <div id={pictureId} aria-live="polite" className="min-w-0 lg:col-span-7">
                <div key={f.title} className="animate-fade-in">
                  <Picture src={f.photo} alt={f.title} label={f.label ?? f.title} ratio="4/3" />
                  {f.points?.length ? (
                    <ul className="mt-6 flex flex-wrap gap-x-8 gap-y-3">
                      {f.points.map((p) => (
                        <li key={p} className="inline-flex items-center gap-2 text-sm font-medium text-ink">
                          <Check className="size-4 text-ok" aria-hidden="true" />
                          {p}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "checklist") {
    return (
      <Section block="features_split" variant={variant} tone={tone ?? "plain"}>
        <Container>
          <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-20">
            <div className="relative order-2 lg:order-1">
              <Picture src={d.photo || undefined} alt={d.title} label="Our work, up close" ratio="4/5" />
              <div className="absolute -bottom-6 left-4 right-4 rounded-card border border-line bg-surface p-5 shadow-card sm:left-auto sm:right-6 sm:max-w-64">
                <p className="font-head text-4xl font-semibold tracking-tight text-ink">
                  <NumberTicker value={d.stat.value} suffix={d.stat.suffix} />
                </p>
                <p className="mt-1 text-sm leading-snug text-muted">{d.stat.label}</p>
              </div>
            </div>
            <div className="order-1 min-w-0 lg:order-2">
              <SectionHead title={d.title} intro={d.intro} className="mb-8 sm:mb-10" />
              <ul className="divide-y divide-line border-y border-line">
                {d.checklist.map((c) => (
                  <li key={c} className="flex items-start gap-4 py-4">
                    <span className="mt-0.5 inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                      <Check className="size-3.5" aria-hidden="true" />
                    </span>
                    <span className="text-base text-ink">{c}</span>
                  </li>
                ))}
              </ul>
              <a
                href={d.action.href}
                className="mt-8 inline-flex min-h-10 items-center gap-2 font-semibold text-primary underline-offset-4 hover:underline"
              >
                {d.action.label}
                <ArrowRight className="size-4" aria-hidden="true" />
              </a>
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="features_split" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={d.title} intro={d.intro} />
        <div className="flex flex-col gap-16 sm:gap-24">
          {d.features.map((f, i) => (
            <article key={f.title} className="grid items-center gap-8 lg:grid-cols-12 lg:gap-16">
              <div className={cn("lg:col-span-6", i % 2 === 1 && "lg:order-2 lg:col-start-7")}>
                <Picture src={f.photo} alt={f.title} label={f.label ?? f.title} ratio="3/2" />
              </div>
              <div className={cn("min-w-0 lg:col-span-5", i % 2 === 1 ? "lg:order-1 lg:col-start-1" : "lg:col-start-8")}>
                <p className="font-head text-sm font-semibold tabular-nums text-primary">{String(i + 1).padStart(2, "0")}</p>
                <h3 className="mt-3 font-head text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{f.title}</h3>
                <p className="mt-4 text-lg leading-relaxed text-muted">{f.text}</p>
                {f.points?.length ? (
                  <ul className="mt-6 flex flex-col gap-3">
                    {f.points.map((p) => (
                      <li key={p} className="flex items-center gap-3 text-ink">
                        <Check className="size-4 shrink-0 text-ok" aria-hidden="true" />
                        {p}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </Container>
    </Section>
  );
}
