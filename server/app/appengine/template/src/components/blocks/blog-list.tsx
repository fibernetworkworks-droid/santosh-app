// v0.999.51 D1 the kit: Blog / updates - one featured post beside a dated list, cards with category chips, or a
// plain notice board grouped by month. Dates are hers; a post links to its own page.
import * as React from "react";
import { format, isValid, parseISO } from "date-fns";
import { ArrowRight, ArrowUpRight, Pin } from "lucide-react";
import { Section, Container, SectionHead, Picture, type Tone } from "./_kit";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const variants = ["featured", "cards", "notice"] as const;
export type BlogListVariant = (typeof variants)[number];

export interface Post {
  title: string;
  excerpt?: string;
  /** ISO date, e.g. 2026-11-12 */
  date: string;
  category?: string;
  readMins?: number;
  href?: string;
  image?: string;
  /** keep at the top of the notice board */
  pinned?: boolean;
}

export interface BlogListProps {
  variant?: BlogListVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  posts?: Post[];
  allLabel?: string;
  action?: { label: string; href: string };
}

export const sample: Required<Omit<BlogListProps, "variant" | "tone">> = {
  title: "Notes from the clinic",
  intro: "Short, practical reads from our doctors - and the notices you need before your next visit.",
  allLabel: "All",
  action: { label: "See all posts", href: "#blog" },
  posts: [
    {
      title: "Cold mornings and your knees: what actually helps",
      excerpt: "Why knee pain rises when the mornings turn cold, and the four exercises our physiotherapist gives every patient in winter.",
      date: "2026-11-10",
      category: "Health tips",
      readMins: 5,
      href: "#blog",
    },
    {
      title: "Clinic closed on Guru Nanak Jayanti",
      excerpt: "The clinic stays closed on Friday. Emergency calls go to Dr. Rao's mobile as usual.",
      date: "2026-11-04",
      category: "Notices",
      href: "#blog",
      pinned: true,
    },
    {
      title: "Diabetes check camp - free HbA1c test",
      excerpt: "Saturday 22 November, 9 am to 1 pm. Come on an empty stomach and bring your last reports.",
      date: "2026-10-28",
      category: "Events",
      readMins: 2,
      href: "#blog",
    },
    {
      title: "How much water does a child really need?",
      excerpt: "A simple guide by age, and the signs of dehydration to watch for after school.",
      date: "2026-10-15",
      category: "Health tips",
      readMins: 4,
      href: "#blog",
    },
    {
      title: "New evening hours on Tuesdays",
      excerpt: "Dr. Kulkarni now sees patients till 9 pm on Tuesdays. Book by phone or WhatsApp.",
      date: "2026-10-02",
      category: "Notices",
      href: "#blog",
    },
  ],
};

function soft(tone?: Tone) {
  return tone === "primary" || tone === "ink" ? "opacity-75" : "text-muted";
}

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function day(iso: string, pattern = "d MMM yyyy") {
  const d = parseISO(iso);
  return isValid(d) ? format(d, pattern) : iso;
}

function Meta({ post, className }: { post: Post; className?: string }) {
  return (
    <p className={cn("flex flex-wrap items-center gap-x-2 gap-y-1 text-sm", className)}>
      <time dateTime={post.date}>{day(post.date)}</time>
      {post.readMins ? (
        <>
          <span aria-hidden="true">·</span>
          <span>{post.readMins} min read</span>
        </>
      ) : null}
    </p>
  );
}

export default function BlogList({ variant = "featured", tone, ...rest }: BlogListProps) {
  const p = { ...sample, ...given(rest) };
  const muted = soft(tone);
  const posts = React.useMemo(() => [...p.posts].sort((a, b) => b.date.localeCompare(a.date)), [p.posts]);
  const cats = React.useMemo(() => Array.from(new Set(posts.map((x) => x.category).filter((c): c is string => !!c))), [posts]);
  const [active, setActive] = React.useState(p.allLabel);

  if (variant === "cards") {
    const shown = active === p.allLabel ? posts : posts.filter((x) => x.category === active);
    return (
      <Section block="blog_list" variant={variant} tone={tone ?? "surface"} className="[&_h2]:text-inherit">
        <Container>
          <SectionHead title={p.title} intro={p.intro} />
          {cats.length > 1 ? (
            <div role="group" aria-label="Filter posts" className="-mt-4 mb-8 flex flex-wrap gap-2">
              {[p.allLabel, ...cats].map((c) => {
                const on = c === active;
                return (
                  <button
                    key={c}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setActive(c)}
                    className={cn(
                      "h-10 rounded-full border px-4 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                      on ? "border-ink bg-ink text-bg" : "border-line bg-bg text-ink hover:border-ink/40",
                    )}
                  >
                    {c}
                  </button>
                );
              })}
            </div>
          ) : null}
          <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {shown.map((post) => (
              <li key={post.title} className="min-w-0">
                <a
                  href={post.href ?? "#blog"}
                  className="group flex h-full flex-col overflow-hidden rounded-card border border-line bg-bg text-ink transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                >
                  <Picture src={post.image} alt="" ratio="16/9" className="rounded-none" />
                  <div className="flex flex-1 flex-col gap-3 p-5">
                    {post.category ? <Badge tone="neutral">{post.category}</Badge> : null}
                    <h3 className="font-head text-lg font-semibold leading-snug break-words">{post.title}</h3>
                    {post.excerpt ? <p className="line-clamp-3 text-sm text-muted">{post.excerpt}</p> : null}
                    <Meta post={post} className="mt-auto pt-2 text-muted" />
                  </div>
                </a>
              </li>
            ))}
          </ul>
        </Container>
      </Section>
    );
  }

  if (variant === "notice") {
    const ordered = [...posts.filter((x) => x.pinned), ...posts.filter((x) => !x.pinned)];
    const months = new Map<string, Post[]>();
    for (const post of ordered) {
      const k = post.pinned ? "Pinned" : day(post.date, "MMMM yyyy");
      months.set(k, [...(months.get(k) ?? []), post]);
    }
    return (
      <Section block="blog_list" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
        <Container className="max-w-3xl">
          <SectionHead title={p.title} intro={p.intro} />
          <div className="flex flex-col gap-10">
            {Array.from(months.entries()).map(([month, list]) => (
              <div key={month} role="group" aria-labelledby={`notice-${month.replace(/\s+/g, "-")}`}>
                <h3
                  id={`notice-${month.replace(/\s+/g, "-")}`}
                  className={cn("mb-3 flex items-center gap-2 text-sm font-semibold text-inherit", month === "Pinned" ? "text-primary" : "")}
                >
                  {month === "Pinned" ? <Pin className="size-4" aria-hidden="true" /> : null}
                  {month}
                </h3>
                <ul className="divide-y divide-line border-y border-line">
                  {list.map((post) => (
                    <li key={post.title}>
                      <a
                        href={post.href ?? "#blog"}
                        className="group grid grid-cols-1 gap-1 py-4 text-inherit transition-colors hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary sm:grid-cols-6 sm:gap-6 sm:px-2"
                      >
                        <time dateTime={post.date} className={cn("text-sm tabular-nums sm:col-span-1 sm:pt-0.5", muted)}>
                          {day(post.date, "d MMM")}
                        </time>
                        <span className="flex min-w-0 flex-col gap-1 sm:col-span-5">
                          <span className="flex items-start justify-between gap-3">
                            <span className="font-medium break-words">{post.title}</span>
                            <ArrowUpRight className="mt-0.5 size-4 shrink-0 opacity-50 transition-opacity group-hover:opacity-100" aria-hidden="true" />
                          </span>
                          {post.excerpt ? <span className={cn("text-sm", muted)}>{post.excerpt}</span> : null}
                        </span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Container>
      </Section>
    );
  }

  const [lead, ...others] = posts;
  return (
    <Section block="blog_list" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
      <Container>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
          <Button variant="outline" asChild className="self-start sm:self-auto border-current/25 text-inherit hover:bg-current/5">
            <a href={p.action.href}>
              {p.action.label} <ArrowRight className="size-4" aria-hidden="true" />
            </a>
          </Button>
        </div>
        <div className="mt-10 grid gap-10 lg:grid-cols-12 lg:gap-12">
          {lead ? (
            <a
              href={lead.href ?? "#blog"}
              className="group flex min-w-0 flex-col gap-5 text-inherit focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary lg:col-span-7"
            >
              <span className="block overflow-hidden rounded-card">
                <Picture src={lead.image} alt="" label={lead.category} ratio="3/2" className="transition-transform duration-500 group-hover:scale-105" />
              </span>
              <span className="flex flex-col gap-3">
                {lead.category ? <span className="text-sm font-medium text-primary">{lead.category}</span> : null}
                <span className="font-head text-2xl font-semibold leading-tight tracking-tight sm:text-3xl">{lead.title}</span>
                {lead.excerpt ? <span className={cn("text-base", muted)}>{lead.excerpt}</span> : null}
                <Meta post={lead} className={muted} />
              </span>
            </a>
          ) : null}
          <ul className="flex min-w-0 flex-col divide-y divide-line border-t border-line lg:col-span-5 lg:border-t-0">
            {others.slice(0, 4).map((post) => (
              <li key={post.title} className="py-5 lg:first:pt-0">
                <a
                  href={post.href ?? "#blog"}
                  className="group flex flex-col gap-2 text-inherit focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                >
                  <span className={cn("flex items-center gap-2 text-xs font-medium", muted)}>
                    {post.category ? <span>{post.category}</span> : null}
                    {post.category ? <span aria-hidden="true">·</span> : null}
                    <time dateTime={post.date}>{day(post.date)}</time>
                  </span>
                  <h3 className="font-head text-lg font-semibold leading-snug text-inherit underline-offset-4 group-hover:underline">
                    {post.title}
                  </h3>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </Container>
    </Section>
  );
}
