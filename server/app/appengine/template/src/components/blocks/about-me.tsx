// v0.999.79 D8 wave 3 block: About me - the person is the site: her photo, her name, her story in her own words, a few
// facts about her, and one way to reach her. Two layouts: photo beside the story, or the story centred under the photo.
import * as React from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Section, Container, Picture, type Tone } from "./_kit";

export const variants = ["split", "centered"] as const;
export type AboutMeVariant = (typeof variants)[number];

export interface AboutMeProps {
  variant?: AboutMeVariant;
  tone?: Tone;
  name?: string;
  role?: string;
  story?: string[];
  facts?: string[];
  photo?: { src: string; alt: string };
  action?: { label: string; href: string };
}

export const sample: Required<Omit<AboutMeProps, "variant" | "tone">> = {
  name: "Ananya Kulkarni",
  role: "Illustrator and picture book maker",
  story: [
    "I draw stories for children, mostly about the small things a city forgets to look at.",
    "Twelve years, nine books and many school walls later, I still begin every picture with a pencil.",
  ],
  facts: ["Based in Pune", "Nine picture books", "Workshops in English and Marathi"],
  photo: { src: "", alt: "Ananya at her drawing desk" },
  action: { label: "Work with me", href: "#contact" },
};

export default function AboutMe({ variant = "split", tone, ...rest }: AboutMeProps) {
  const p = { ...sample, ...rest };
  const centered = variant === "centered";
  return (
    <Section block="about_me" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <div className={cn("grid gap-10", centered ? "mx-auto max-w-2xl justify-items-center text-center" : "items-center lg:grid-cols-12 lg:gap-16")}>
          <div className={cn(centered ? "w-48 sm:w-56" : "lg:col-span-5")}>
            <Picture src={p.photo?.src} alt={p.photo?.alt || p.name} ratio={centered ? "1/1" : "4/5"} label={p.name}
              className={centered ? "rounded-full" : undefined} />
          </div>
          <div className={cn("flex flex-col gap-5", centered ? "items-center" : "lg:col-span-7")}>
            <div className="flex flex-col gap-2">
              <h2 className="text-balance font-head text-3xl font-semibold tracking-tight sm:text-4xl">{p.name}</h2>
              {p.role ? <p className="text-lg text-primary">{p.role}</p> : null}
            </div>
            <div className="flex max-w-prose flex-col gap-4 text-base leading-relaxed text-muted sm:text-lg">
              {p.story.map((s, i) => (
                <p key={i}>{s}</p>
              ))}
            </div>
            {p.facts.length ? (
              <ul className={cn("flex flex-wrap gap-2", centered && "justify-center")}>
                {p.facts.map((f) => (
                  <li key={f} className="rounded-control border border-line bg-surface px-3 py-1.5 text-sm">{f}</li>
                ))}
              </ul>
            ) : null}
            {p.action?.href ? (
              <Button asChild size="lg" className="w-fit">
                <a href={p.action.href}>
                  {p.action.label}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </a>
              </Button>
            ) : null}
          </div>
        </div>
      </Container>
    </Section>
  );
}
