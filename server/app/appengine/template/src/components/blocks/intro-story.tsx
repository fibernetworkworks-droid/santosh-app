// v0.999.51 D1 the kit: the story / about block, in her own words. Three layouts: portrait (her photo beside her
// story, a signed line), timeline (her years, one line each - only her dates), quote (a pull quote in large type over
// a photo of the place, two short paragraphs). The words rise in once as they scroll into view.
import * as React from "react";
import { Quote } from "lucide-react";
import { Reveal } from "@/components/effects";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, Picture, type Tone } from "./_kit";

export const variants = ["portrait", "timeline", "quote"] as const;
export type IntroStoryVariant = (typeof variants)[number];

export interface StoryPhoto {
  src?: string;
  alt: string;
  label: string;
}

export interface StoryYear {
  year: string;
  line: string;
}

export interface IntroStoryProps {
  variant?: IntroStoryVariant;
  tone?: Tone;
  title?: string;
  /** her story, a few short paragraphs (the first one is set larger) */
  story?: string[];
  owner?: { name: string; role: string };
  photo?: StoryPhoto;
  /** a photo of the place (quote layout) */
  place?: StoryPhoto;
  /** the line she signs off with */
  signoff?: string;
  /** her own dates, one line each */
  years?: StoryYear[];
  quote?: string;
}

export const sample: Required<Omit<IntroStoryProps, "variant" | "tone">> = {
  title: "How a home kitchen became a bakery",
  story: [
    "I started baking for neighbours in 2014, from a two-burner kitchen in our flat on Paud Road.",
    "Word went round the society, then the next one. In 2017 we rented a small shop on Karve Road and bought a proper deck oven.",
    "We still bake the old way: slow dough, no premixes, butter we can name. Most of our team has been with us for more than five years.",
  ],
  owner: { name: "Meera Kulkarni", role: "Founder and head baker" },
  photo: { alt: "Meera in the bakery kitchen, shaping dough", label: "Owner photo" },
  place: { alt: "The front of the bakery on Karve Road in the morning", label: "Photo of the place" },
  signoff: "Come in early, the pav is still warm.",
  years: [
    { year: "2014", line: "First cakes from home, ordered by phone." },
    { year: "2017", line: "The Karve Road shop opens with one deck oven." },
    { year: "2020", line: "Home delivery starts across Kothrud and Warje." },
    { year: "2024", line: "A second oven and a team of eleven." },
  ],
  quote: "We bake only what we would put on our own family's table, and we sell it the same morning.",
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

export default function IntroStory({ variant = "portrait", tone, ...rest }: IntroStoryProps) {
  const p = withSample(sample, rest);
  const t = tone ?? "plain";
  const [first, ...more] = p.story;

  if (variant === "timeline") {
    return (
      <Section block="intro_story" variant={variant} tone={t}>
        <Container>
          <div className="grid gap-8 lg:grid-cols-12 lg:gap-16">
            <SectionHead title={p.title} className="mb-0 lg:col-span-5" />
            <div className={cn("space-y-4 text-lg leading-relaxed lg:col-span-7", quiet(t))}>
              {p.story.slice(0, 2).map((x) => (
                <p key={x}>{x}</p>
              ))}
            </div>
          </div>
          <ol className="mt-14 grid gap-0 sm:mt-20 sm:grid-cols-2 lg:grid-cols-4">
            {p.years.map((y, i) => (
              <li key={y.year + y.line} className="relative border-l border-line pb-10 pl-6 sm:border-l-0 sm:border-t sm:pb-0 sm:pl-0 sm:pr-8 sm:pt-8">
                <span aria-hidden="true" className="absolute -left-1.5 top-1 size-3 rounded-full bg-primary sm:-top-1.5 sm:left-0" />
                <Reveal delay={i * 120}>
                  <p className="font-head text-4xl font-semibold tracking-tight text-primary sm:text-5xl">{y.year}</p>
                  <p className={cn("mt-3 max-w-xs text-base leading-relaxed", quiet(t))}>{y.line}</p>
                </Reveal>
              </li>
            ))}
          </ol>
        </Container>
      </Section>
    );
  }

  if (variant === "quote") {
    return (
      <Section block="intro_story" variant={variant} tone={t}>
        <Container>
          <Reveal>
            <figure className="max-w-4xl">
              <Quote className="size-10 text-primary" aria-hidden="true" />
              <blockquote className="mt-6 break-words font-head text-3xl font-medium leading-snug tracking-tight sm:text-5xl sm:leading-tight">
                {p.quote}
              </blockquote>
              <figcaption className={cn("mt-6 text-base", quiet(t))}>
                <span className="font-medium">{p.owner.name}</span>, {p.owner.role}
              </figcaption>
            </figure>
          </Reveal>
          <div className="mt-14 grid items-start gap-10 sm:mt-20 lg:grid-cols-12 lg:gap-16">
            <Picture src={p.place.src} alt={p.place.alt} label={p.place.label} ratio="3/2" className="lg:col-span-7" />
            <div className="min-w-0 lg:col-span-5 lg:pt-6">
              <h2 className="font-head text-2xl font-semibold tracking-tight sm:text-3xl">{p.title}</h2>
              <div className={cn("mt-5 space-y-4 text-base leading-relaxed", quiet(t))}>
                {p.story.map((x) => (
                  <p key={x}>{x}</p>
                ))}
              </div>
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="intro_story" variant={variant} tone={t}>
      <Container>
        <div className="grid items-start gap-12 lg:grid-cols-12 lg:gap-20">
          <figure className="min-w-0 lg:col-span-5 lg:sticky lg:top-24">
            <Picture src={p.photo.src} alt={p.photo.alt} label={p.photo.label} ratio="3/4" />
            <figcaption className="mt-4 flex items-baseline justify-between gap-4 border-b border-line pb-4">
              <span className="font-medium">{p.owner.name}</span>
              <span className={cn("text-right text-sm", quiet(t))}>{p.owner.role}</span>
            </figcaption>
          </figure>
          <Reveal className="min-w-0 lg:col-span-7 lg:pt-8">
            <h2 className="font-head text-3xl font-semibold tracking-tight sm:text-5xl sm:leading-tight">{p.title}</h2>
            <p className="mt-8 text-xl leading-relaxed sm:text-2xl sm:leading-relaxed">{first}</p>
            <div className={cn("mt-6 space-y-5 text-lg leading-relaxed", quiet(t))}>
              {more.map((x) => (
                <p key={x}>{x}</p>
              ))}
            </div>
            <p className="mt-10 font-head text-2xl italic tracking-tight text-primary">{p.signoff}</p>
            <p className={cn("mt-2 text-sm", quiet(t))}>{p.owner.name}</p>
          </Reveal>
        </div>
      </Container>
    </Section>
  );
}
