"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 the kit: what her customers said (real reviews only - the sample is marked as a sample). Three
// layouts: cards (a masonry of quotes with name and area), spotlight (one large quote at a time, previous / next),
// summary (the rating she gives beside three quotes).
import * as React from "react";
import { ChevronLeft, ChevronRight, Star } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["cards", "spotlight", "summary"] as const;
export type ReviewsVariant = (typeof variants)[number];

export interface ReviewItem {
  quote: string;
  name: string;
  /** her customer's area or city */
  area?: string;
  /** 1 to 5, only when the review had stars */
  stars?: number;
  /** when it was written: "March 2025" */
  when?: string;
}

export interface ReviewsProps {
  variant?: ReviewsVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  reviews?: ReviewItem[];
  /** the rating she gives, from where (summary) */
  rating?: { score: number; count: number; source: string };
  /** a small line under the heading; the sample says it is a sample */
  note?: string;
}

export const sample: Required<Omit<ReviewsProps, "variant" | "tone">> = {
  title: "What families tell us",
  intro: "Words from parents whose children study with us.",
  reviews: [
    { quote: "My daughter was scared of maths in class 8. By the board exams she was the one explaining sums to her friends.", name: "Sunita R.", area: "Vaishali Nagar, Jaipur", stars: 5, when: "April 2025" },
    { quote: "Small batches, so the teacher actually knows every child's name and where they get stuck.", name: "Imran K.", area: "Malviya Nagar", stars: 5, when: "January 2025" },
    { quote: "The weekly test reports on WhatsApp are simple and honest. I always know how he is doing.", name: "Priya Sharma", area: "Mansarovar", stars: 5, when: "November 2024" },
    { quote: "Fees are fair and there are no surprise charges. They even ran extra classes before the exam for free.", name: "Rakesh Meena", area: "C-Scheme", stars: 4, when: "March 2025" },
    { quote: "Two years here and his science marks went from 61 to 88. He now wants to study engineering.", name: "Anjali T.", area: "Raja Park", stars: 5, when: "May 2025" },
    { quote: "Teachers reply to questions even on Sunday. That kind of care is rare.", name: "Deepak Jain", area: "Bani Park", stars: 5, when: "February 2025" },
  ],
  rating: { score: 4.9, count: 214, source: "Google" },
  note: "Sample reviews. Your own customers' words appear here once you add them.",
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

function Stars({ n, className }: { n?: number; className?: string }) {
  if (!n) return null;
  const k = Math.max(0, Math.min(5, Math.round(n)));
  return (
    <span className={cn("inline-flex items-center gap-0.5", className)} role="img" aria-label={`${k} out of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => (
        <Star key={i} className={cn("size-4", i < k ? "fill-accent text-accent" : "text-line")} aria-hidden="true" />
      ))}
    </span>
  );
}

function Person({ r, t }: { r: ReviewItem; t: Tone }) {
  return (
    <figcaption className="flex items-center gap-3">
      <Avatar>
        <AvatarFallback>{initials(r.name)}</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <p className="font-medium leading-tight">{r.name}</p>
        <p className={cn("mt-0.5 text-sm", quiet(t))}>{[r.area, r.when].filter(Boolean).join(" · ")}</p>
      </div>
    </figcaption>
  );
}

export default function Reviews({ variant = "cards", tone, ...rest }: ReviewsProps) {
  const p = withSample(sample, rest);
  const t = tone ?? "plain";
  const [i, setI] = React.useState(0);

  if (variant === "spotlight") {
    const n = p.reviews.length;
    const r = p.reviews[((i % n) + n) % n];
    if (!r) return null;
    return (
      <Section block="reviews" variant={variant} tone={t}>
        <Container className="max-w-4xl">
          <h2 className="text-center font-head text-xl font-semibold tracking-tight sm:text-2xl">{p.title}</h2>
          {p.note ? <p className={cn("mt-2 text-center text-sm", quiet(t))}>{p.note}</p> : null}
          <figure key={i} className="mt-12 flex animate-fade-in flex-col items-center text-center" aria-live="polite">
            <Stars n={r.stars} />
            <blockquote className="mt-8 break-words font-head text-2xl font-medium leading-snug tracking-tight sm:text-4xl sm:leading-tight">
              &ldquo;{r.quote}&rdquo;
            </blockquote>
            <div className="mt-10">
              <Person r={r} t={t} />
            </div>
          </figure>
          <div className="mt-12 flex items-center justify-center gap-2 sm:gap-6">
            <Button variant="outline" size="icon" onClick={() => setI((x) => x - 1)} aria-label="Previous review">
              <ChevronLeft className="size-4" aria-hidden="true" />
            </Button>
            <div className="flex items-center">
              {p.reviews.map((x, k) => (
                <button
                  key={x.name + k}
                  type="button"
                  onClick={() => setI(k)}
                  aria-label={`Review ${k + 1} of ${n}`}
                  aria-current={((i % n) + n) % n === k}
                  className="flex size-10 items-center justify-center rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                >
                  <span
                    className={cn(
                      "block h-1.5 rounded-full transition-colors",
                      ((i % n) + n) % n === k ? "w-6 bg-primary" : "w-1.5 bg-current opacity-25",
                    )}
                  />
                </button>
              ))}
            </div>
            <Button variant="outline" size="icon" onClick={() => setI((x) => x + 1)} aria-label="Next review">
              <ChevronRight className="size-4" aria-hidden="true" />
            </Button>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "summary") {
    return (
      <Section block="reviews" variant={variant} tone={t}>
        <Container>
          <div className="grid gap-12 lg:grid-cols-12 lg:gap-20">
            <div className="lg:col-span-4">
              <div className="lg:sticky lg:top-24">
                <h2 className="font-head text-3xl font-semibold tracking-tight sm:text-4xl">{p.title}</h2>
                <div className="mt-8 flex items-end gap-4">
                  <span className="font-head text-7xl font-semibold leading-none tracking-tight tabular-nums">{p.rating.score.toFixed(1)}</span>
                  <div className="pb-1">
                    <Stars n={p.rating.score} />
                    <p className={cn("mt-1.5 text-sm", quiet(t))}>
                      {p.rating.count.toLocaleString("en-IN")} reviews on {p.rating.source}
                    </p>
                  </div>
                </div>
                {p.note ? <p className={cn("mt-8 border-t border-line pt-5 text-sm", quiet(t))}>{p.note}</p> : null}
              </div>
            </div>
            <div className="divide-y divide-line lg:col-span-8">
              {p.reviews.slice(0, 3).map((r) => (
                <figure key={r.name + r.quote} className="py-8 first:pt-0 last:pb-0">
                  <Stars n={r.stars} />
                  <blockquote className="mt-4 text-xl leading-relaxed sm:text-2xl sm:leading-relaxed">&ldquo;{r.quote}&rdquo;</blockquote>
                  <div className="mt-6">
                    <Person r={r} t={t} />
                  </div>
                </figure>
              ))}
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="reviews" variant={variant} tone={t}>
      <Container>
        <SectionHead title={p.title} intro={p.intro}>
          {p.note ? <p className={cn("text-sm", quiet(t))}>{p.note}</p> : null}
        </SectionHead>
        <ul className="columns-1 gap-5 sm:columns-2 lg:columns-3">
          {p.reviews.map((r) => (
            <li key={r.name + r.quote} className="mb-5 break-inside-avoid">
              <figure className="rounded-card border border-line bg-surface p-7 text-ink shadow-card transition-transform duration-300 hover:-translate-y-0.5">
                <Stars n={r.stars} />
                <blockquote className="mt-4 text-base leading-relaxed">{r.quote}</blockquote>
                <div className="mt-6 border-t border-line pt-5">
                  <Person r={r} t="plain" />
                </div>
              </figure>
            </li>
          ))}
        </ul>
      </Container>
    </Section>
  );
}
