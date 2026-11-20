// v0.999.51 D1 block: FAQ. Three layouts - one centred accordion, a split with the heading held on the left, and a
// search box + topic chips over the accordion (the questions filter as she types).
import * as React from "react";
import { MessageCircle, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["accordion", "split", "search"] as const;
export type FaqVariant = (typeof variants)[number];

export interface FaqItem {
  q: string;
  a: string;
  topic?: string;
}

export interface FaqProps {
  variant?: FaqVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  items?: FaqItem[];
  contactLine?: string;
  contactLabel?: string;
  contactHref?: string;
}

export const sample: Required<Omit<FaqProps, "variant" | "tone">> = {
  title: "Questions people ask us",
  intro: "Short answers to what comes up most. Anything else, message us and a person replies.",
  items: [
    { topic: "Booking", q: "How do I book a slot?", a: "Pick a free time on this page or send us a WhatsApp message with the day you want. We confirm within an hour during working hours." },
    { topic: "Booking", q: "Can I change or cancel my time?", a: "Yes. Tell us at least three hours before and we move it at no cost. Late changes are fine too; we only ask that you let us know." },
    { topic: "Payment", q: "Which payment modes do you take?", a: "UPI, cards and cash. A GST bill is given for every payment, and we can mail it to you." },
    { topic: "Payment", q: "Do I pay anything in advance?", a: "Not for a first visit. For packages we take a small advance, which is adjusted in the final bill." },
    { topic: "Visiting", q: "Where exactly are you, and is there parking?", a: "First floor, Shanti Complex, opposite the Ramdaspeth post office in Nagpur. Two-wheeler parking is in front; cars can use the lane behind the building." },
    { topic: "Visiting", q: "Are you open on Sundays?", a: "Sundays 10 am to 2 pm. We are closed on the three national holidays and on Diwali day." },
  ],
  contactLine: "Did not find your question?",
  contactLabel: "Ask on WhatsApp",
  contactHref: "#contact",
};

function List({ items, cols }: { items: FaqItem[]; cols?: boolean }) {
  return (
    <Accordion type="single" collapsible className={cn("w-full", cols && "lg:columns-2 lg:gap-12")}>
      {items.map((it, i) => (
        <AccordionItem key={it.q} value={`q${i}`} className="break-inside-avoid">
          <AccordionTrigger className="py-5 text-base font-semibold sm:text-lg">{it.q}</AccordionTrigger>
          <AccordionContent className="max-w-prose pb-6 text-base leading-relaxed">{it.a}</AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}

function Ask({ line, label, href, className }: { line: string; label: string; href: string; className?: string }) {
  return (
    <p className={cn("flex flex-wrap items-center gap-x-3 gap-y-2 text-muted", className)}>
      <span>{line}</span>
      <a href={href} className="inline-flex min-h-10 items-center gap-2 font-medium text-primary underline-offset-4 hover:underline">
        <MessageCircle className="size-4" aria-hidden="true" />
        {label}
      </a>
    </p>
  );
}

export default function Faq({ variant = "accordion", tone, ...rest }: FaqProps) {
  const d = { ...sample, ...rest };
  const topics = React.useMemo(() => Array.from(new Set(d.items.map((it) => it.topic).filter((t): t is string => !!t))), [d.items]);
  const [query, setQuery] = React.useState("");
  const [topic, setTopic] = React.useState<string>("All");
  const searchId = React.useId();

  if (variant === "split") {
    return (
      <Section block="faq" variant={variant} tone={tone ?? "plain"}>
        <Container>
          <div className="grid gap-10 lg:grid-cols-12 lg:gap-16">
            <div className="lg:col-span-4">
              <div className="lg:sticky lg:top-24">
                <SectionHead title={d.title} intro={d.intro} className="mb-6 sm:mb-8" />
                <Ask line={d.contactLine} label={d.contactLabel} href={d.contactHref} />
              </div>
            </div>
            <div className="min-w-0 border-t border-line lg:col-span-8">
              <List items={d.items} />
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "search") {
    const q = query.trim().toLowerCase();
    const shown = d.items.filter(
      (it) => (topic === "All" || it.topic === topic) && (!q || it.q.toLowerCase().includes(q) || it.a.toLowerCase().includes(q)),
    );
    return (
      <Section block="faq" variant={variant} tone={tone ?? "surface"}>
        <Container className="max-w-3xl">
          <SectionHead title={d.title} intro={d.intro} />
          <div className="relative">
            <label htmlFor={searchId} className="sr-only">
              Search the questions
            </label>
            <Search className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted" aria-hidden="true" />
            <Input
              id={searchId}
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a word, like parking or UPI"
              className="h-12 pl-12 pr-12 text-base"
            />
            {query ? (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear the search"
                className="absolute right-1 top-1/2 inline-flex size-10 -translate-y-1/2 items-center justify-center rounded-control text-muted transition-colors hover:text-ink"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            ) : null}
          </div>
          {topics.length > 1 ? (
            <div role="group" aria-label="Topics" className="mt-4 flex flex-wrap gap-2">
              {["All", ...topics].map((t) => (
                <button
                  key={t}
                  type="button"
                  aria-pressed={topic === t}
                  onClick={() => setTopic(t)}
                  className={cn(
                    "inline-flex h-10 items-center rounded-full border px-4 text-sm font-medium transition-colors",
                    topic === t ? "border-ink bg-ink text-bg" : "border-line bg-bg text-ink hover:border-ink/40",
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
          ) : null}
          <p className="mt-6 text-sm text-muted" aria-live="polite">
            {shown.length === d.items.length ? `${shown.length} questions` : `${shown.length} of ${d.items.length} questions`}
          </p>
          <div className="mt-2 border-t border-line">
            {shown.length ? (
              <List key={`${topic}-${q}`} items={shown} />
            ) : (
              <div className="flex flex-col items-start gap-3 py-10">
                <p className="text-base text-ink">No question matches "{query}".</p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setQuery("");
                    setTopic("All");
                  }}
                >
                  Show every question
                </Button>
              </div>
            )}
          </div>
          <Ask line={d.contactLine} label={d.contactLabel} href={d.contactHref} className="mt-8" />
        </Container>
      </Section>
    );
  }

  return (
    <Section block="faq" variant={variant} tone={tone ?? "plain"}>
      <Container className="max-w-3xl">
        <SectionHead title={d.title} intro={d.intro} align="center" />
        <div className="border-t border-line">
          <List items={d.items} />
        </div>
        <Ask line={d.contactLine} label={d.contactLabel} href={d.contactHref} className="mt-10 justify-center text-center" />
      </Container>
    </Section>
  );
}
