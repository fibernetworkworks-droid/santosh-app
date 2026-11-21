// v0.999.78 D8 block: Article - one blog post as a page to read: title, date, reading time, author, category, then the
// post itself as plain headings, paragraphs, lists and quotes (Hoola turns her post into these parts in code: no HTML
// from anywhere reaches the page). One layout, made for reading: a narrow column, generous line height.
import * as React from "react";
import { ArrowLeft } from "lucide-react";
import { Section, Container, Picture, type Tone } from "./_kit";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export const variants = ["reading"] as const;
export type ArticleVariant = (typeof variants)[number];

/** one part of the post: "h2" / "h3" heading, "p" paragraph, "li" / "ol" list item, "quote" (anything else = a
 * paragraph; a string so the post's data file can be read as it is) */
export interface ArticlePart {
  k: string;
  t: string;
}

export interface ArticleProps {
  variant?: ArticleVariant;
  tone?: Tone;
  title?: string;
  date?: string;
  minutes?: number;
  author?: string;
  category?: string;
  parts?: ArticlePart[];
  /** v0.999.82: her cover photo (./photos/<name>.webp) */
  cover?: string;
  back?: { label: string; href: string };
}

export const sample: Required<Omit<ArticleProps, "variant" | "tone">> = {
  title: "Why our sourdough rests for a day and a half",
  date: "12 November 2026",
  minutes: 3,
  author: "The bakery team",
  category: "Baking",
  parts: [
    { k: "p", t: "A slow rise gives the bread its open crumb and a crust that cracks when you press it." },
    { k: "h2", t: "What the long rest does" },
    { k: "p", t: "The dough keeps working while it waits: flavour builds and the loaf keeps for longer." },
    { k: "li", t: "Mixed in the afternoon" },
    { k: "li", t: "Shaped the next morning" },
    { k: "li", t: "Baked at dawn on the third day" },
    { k: "quote", t: "Good bread cannot be hurried." },
  ],
  cover: "",
  back: { label: "All posts", href: "./blog" },
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

/** consecutive list items become one list */
function groups(parts: ArticlePart[]): (ArticlePart | { k: "ul" | "olist"; items: string[] })[] {
  const out: (ArticlePart | { k: "ul" | "olist"; items: string[] })[] = [];
  for (const p of parts) {
    const kind = p.k === "li" ? "ul" : p.k === "ol" ? "olist" : "";
    const last = out[out.length - 1];
    if (kind && last && "items" in last && last.k === kind) last.items.push(p.t);
    else if (kind) out.push({ k: kind as "ul" | "olist", items: [p.t] });
    else out.push(p);
  }
  return out;
}

export default function Article({ variant = "reading", tone, ...rest }: ArticleProps) {
  const p = withSample(sample, rest);
  const t = tone ?? "plain";
  const meta = [p.date, p.minutes ? `${p.minutes} min read` : "", p.author].filter(Boolean).join(" · ");
  return (
    <Section block="article" variant={variant} tone={t}>
      <Container>
        <article className="mx-auto max-w-2xl">
          {p.back?.href ? (
            <a
              href={p.back.href}
              className="inline-flex items-center gap-1.5 text-sm font-medium text-muted no-underline transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            >
              <ArrowLeft className="size-4" aria-hidden="true" />
              {p.back.label}
            </a>
          ) : null}
          {p.category ? (
            <div className="mt-6">
              <Badge tone="outline">{p.category}</Badge>
            </div>
          ) : null}
          <h1 className="mt-4 text-balance font-head text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">{p.title}</h1>
          {meta ? <p className="mt-4 text-sm text-muted">{meta}</p> : null}
          {p.cover ? <Picture src={p.cover} alt={p.title} ratio="16/9" className="mt-8" /> : null}
          <div className="mt-10 flex flex-col gap-5 text-lg leading-relaxed">
            {groups(p.parts).map((x, i) => {
              if ("items" in x) {
                const L = x.k === "olist" ? "ol" : "ul";
                return (
                  <L key={i} className={cn("flex flex-col gap-2 pl-6", x.k === "olist" ? "list-decimal" : "list-disc")}>
                    {x.items.map((it, j) => (
                      <li key={j}>{it}</li>
                    ))}
                  </L>
                );
              }
              if (x.k === "h2") return <h2 key={i} className="mt-6 font-head text-2xl font-semibold tracking-tight">{x.t}</h2>;
              if (x.k === "h3") return <h3 key={i} className="mt-4 font-head text-xl font-semibold tracking-tight">{x.t}</h3>;
              if (x.k === "quote")
                return (
                  <blockquote key={i} className="border-l-2 border-primary pl-5 italic text-muted">
                    {x.t}
                  </blockquote>
                );
              return <p key={i}>{x.t}</p>;
            })}
          </div>
        </article>
      </Container>
    </Section>
  );
}
