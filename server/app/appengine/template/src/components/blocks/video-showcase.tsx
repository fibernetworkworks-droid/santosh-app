"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 the kit: Video - click to play. A poster (her photo, else the design's stand-in) with a play button;
// the video itself is only put on the page after the tap, never autoplayed, and only from her own file.
import * as React from "react";
import { Check, Clock, Play } from "lucide-react";
import { Section, Container, SectionHead, Picture, type Tone } from "./_kit";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";

export const variants = ["feature", "split", "reels"] as const;
export type VideoShowcaseVariant = (typeof variants)[number];

export interface ShowVideo {
  title: string;
  /** her video file; until it is added, a tap says so */
  src?: string;
  /** her poster photo */
  poster?: string;
  duration?: string;
  caption?: string;
}

export interface VideoShowcaseProps {
  variant?: VideoShowcaseVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  videos?: ShowVideo[];
  points?: string[];
  action?: { label: string; href: string };
}

export const sample: Required<Omit<VideoShowcaseProps, "variant" | "tone">> = {
  title: "See how a batch is made",
  intro: "Three minutes in our kitchen in Kolhapur: the masala roasted, ground and packed on the same morning.",
  videos: [
    { title: "A morning in the kitchen", duration: "3:12", caption: "Roasting, grinding and packing - start to finish." },
    { title: "How we pick the chillies", duration: "0:48", caption: "Byadgi and Sankeshwari, bought from two farms near Gadhinglaj." },
    { title: "Packing for courier", duration: "0:36", caption: "Sealed, labelled with the batch date and boxed." },
    { title: "Kolhapuri misal with our masala", duration: "1:05", caption: "Our cook's own recipe, one pan." },
  ],
  points: [
    "Ground in small batches of 20 kg, never stored for months",
    "No colour, no salt filler, no anti-caking powder",
    "Batch date printed on every pack",
  ],
  action: { label: "Order a pack", href: "#contact" },
};

type Ratio = "16/9" | "3/4";
const ASPECT: Record<Ratio, string> = { "16/9": "aspect-video", "3/4": "aspect-3/4" };

function soft(tone?: Tone) {
  return tone === "primary" || tone === "ink" ? "opacity-75" : "text-muted";
}

function given<T extends object>(rest: T): Partial<T> {
  return Object.fromEntries(Object.entries(rest).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function Player({ v, ratio = "16/9", big = false, className }: { v: ShowVideo; ratio?: Ratio; big?: boolean; className?: string }) {
  const [on, setOn] = React.useState(false);
  const ref = React.useRef<HTMLVideoElement>(null);
  React.useEffect(() => {
    if (on) ref.current?.play().catch(() => undefined);
  }, [on]);

  if (on && v.src) {
    return (
      <video
        ref={ref}
        src={v.src}
        poster={v.poster}
        controls
        playsInline
        preload="metadata"
        aria-label={v.title}
        className={cn("w-full rounded-card bg-ink object-cover", ASPECT[ratio], className)}
      />
    );
  }

  const tap = () => {
    if (v.src) setOn(true);
    else toast("This video is not added yet", { description: `"${v.title}" will play here once the video file is added.` });
  };

  return (
    <button
      type="button"
      onClick={tap}
      aria-label={`Play video: ${v.title}${v.duration ? `, ${v.duration}` : ""}`}
      className={cn(
        "group relative block w-full overflow-hidden rounded-card text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
        className,
      )}
    >
      <Picture src={v.poster} alt="" ratio={ratio} className="transition-transform duration-700 group-hover:scale-105" />
      <span aria-hidden="true" className="absolute inset-0 bg-ink/15 transition-colors group-hover:bg-ink/25" />
      <span className="absolute inset-0 flex items-center justify-center">
        <span
          className={cn(
            "flex items-center justify-center rounded-full bg-surface text-ink shadow-card transition-transform duration-300 group-hover:scale-105",
            big ? "size-20" : "size-14",
          )}
        >
          <Play className={cn("translate-x-0.5 fill-ink", big ? "size-7" : "size-5")} aria-hidden="true" />
        </span>
      </span>
      {v.duration ? (
        <span className="absolute bottom-3 left-3 inline-flex items-center gap-1 rounded-control bg-ink/70 px-2 py-1 text-xs font-medium text-bg tabular-nums">
          <Clock className="size-3" aria-hidden="true" />
          {v.duration}
        </span>
      ) : null}
    </button>
  );
}

export default function VideoShowcase({ variant = "feature", tone, ...rest }: VideoShowcaseProps) {
  const p = { ...sample, ...given(rest) };
  const muted = soft(tone);
  const lead = p.videos[0];

  if (variant === "split") {
    return (
      <Section block="video_showcase" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
        <Container>
          <div className="grid items-center gap-10 lg:grid-cols-12 lg:gap-14">
            <div className="min-w-0 lg:col-span-7">{lead ? <Player v={lead} big /> : null}</div>
            <div className="flex min-w-0 flex-col gap-6 lg:col-span-5">
              <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
              <ul className="flex flex-col gap-3">
                {p.points.map((pt) => (
                  <li key={pt} className="flex gap-3 text-base">
                    <Check className="mt-1 size-4 shrink-0 text-primary" aria-hidden="true" />
                    <span className="min-w-0">{pt}</span>
                  </li>
                ))}
              </ul>
              <div>
                <Button asChild size="lg">
                  <a href={p.action.href}>{p.action.label}</a>
                </Button>
              </div>
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "reels") {
    return (
      <Section block="video_showcase" variant={variant} tone={tone ?? "surface"} className="[&_h2]:text-inherit">
        <Container wide>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
            <a href={p.action.href} className="inline-flex h-10 shrink-0 items-center text-sm font-medium underline-offset-4 hover:underline">
              {p.action.label}
            </a>
          </div>
          <ul className="-mx-4 mt-10 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-4 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 lg:grid-cols-4">
            {p.videos.map((v) => (
              <li key={v.title} className="flex w-64 shrink-0 snap-start flex-col gap-3 sm:w-auto">
                <Player v={v} ratio="3/4" />
                <div className="flex flex-col gap-1">
                  <h3 className="font-head text-base font-semibold text-inherit">{v.title}</h3>
                  {v.caption ? <p className={cn("text-sm", muted)}>{v.caption}</p> : null}
                </div>
              </li>
            ))}
          </ul>
        </Container>
      </Section>
    );
  }

  const more = p.videos.slice(1, 4);
  return (
    <Section block="video_showcase" variant={variant} tone={tone ?? "plain"} className="[&_h2]:text-inherit">
      <Container>
        <SectionHead title={p.title} intro={p.intro} align="center" />
        {lead ? (
          <figure className="flex flex-col gap-3">
            <Player v={lead} big />
            {lead.caption ? (
              <figcaption className={cn("text-center text-sm", muted)}>
                <span className="font-medium text-inherit">{lead.title}</span> - {lead.caption}
              </figcaption>
            ) : null}
          </figure>
        ) : null}
        {more.length ? (
          <ul className="mt-10 grid gap-6 sm:grid-cols-3">
            {more.map((v) => (
              <li key={v.title} className="flex min-w-0 flex-col gap-2">
                <Player v={v} />
                <h3 className="font-head text-base font-semibold text-inherit">{v.title}</h3>
              </li>
            ))}
          </ul>
        ) : null}
      </Container>
    </Section>
  );
}
