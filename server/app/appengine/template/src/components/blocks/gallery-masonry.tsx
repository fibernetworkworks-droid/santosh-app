"use client"; // v0.999.64 D3: needs JavaScript in the browser - on a pre-rendered site page it is an island
// v0.999.51 D1 the kit: her photos. Three layouts: masonry (columns of mixed shapes, tap one to see it large),
// strip (a horizontal film strip that snaps, with previous / next), feature (one big photo and four small ones).
// The large view is a dialog with previous / next and the caption.
import * as React from "react";
import { ChevronLeft, ChevronRight, Expand } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, Picture, type Tone } from "./_kit";

export const variants = ["masonry", "strip", "feature"] as const;
export type GalleryMasonryVariant = (typeof variants)[number];

type Ratio = "1/1" | "4/3" | "3/2" | "16/9" | "3/4" | "4/5";

export interface GalleryPhoto {
  src?: string;
  alt: string;
  /** shown on the stand-in until her photo is there */
  label?: string;
  caption?: string;
  ratio?: Ratio;
}

export interface GalleryMasonryProps {
  variant?: GalleryMasonryVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  photos?: GalleryPhoto[];
}

export const sample: Required<Omit<GalleryMasonryProps, "variant" | "tone">> = {
  title: "Inside the studio",
  intro: "A few days from the last year: workshops, finished pieces and the room where it all happens.",
  photos: [
    { alt: "Clay bowls drying on a wooden rack", label: "Photo 1", caption: "Bowls drying before the first firing", ratio: "3/4" },
    { alt: "A Saturday wheel workshop with eight people", label: "Photo 2", caption: "Saturday wheel class, Bandra", ratio: "4/3" },
    { alt: "Glazed mugs in indigo and white", label: "Photo 3", caption: "Indigo glaze, out of the kiln", ratio: "1/1" },
    { alt: "Hands shaping a pot on the wheel", label: "Photo 4", caption: "Centering takes the longest", ratio: "4/5" },
    { alt: "A shelf of finished planters by the window", label: "Photo 5", caption: "Planters for a cafe in Khar", ratio: "3/2" },
    { alt: "The kiln room with a loaded shelf", label: "Photo 6", caption: "Loading the kiln, 1,240 degrees", ratio: "3/4" },
    { alt: "A table set with handmade plates", label: "Photo 7", caption: "A dinner set made to order", ratio: "4/3" },
  ],
};

function withSample<T extends object>(base: T, over: Partial<T>): T {
  const out = { ...base };
  for (const k of Object.keys(over) as (keyof T)[]) if (over[k] !== undefined) out[k] = over[k] as T[keyof T];
  return out;
}

const quiet = (t: Tone) => (t === "ink" || t === "primary" ? "opacity-80" : "text-muted");

function Lightbox({ photos, index, onIndex }: { photos: GalleryPhoto[]; index: number | null; onIndex: (i: number | null) => void }) {
  const ph = index === null ? undefined : photos[index];
  const go = (d: number) => index !== null && onIndex((index + d + photos.length) % photos.length);
  return (
    <Dialog open={index !== null} onOpenChange={(o) => !o && onIndex(null)}>
      <DialogContent
        className="max-w-4xl p-4 sm:p-6"
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") go(1);
          if (e.key === "ArrowLeft") go(-1);
        }}
      >
        {ph ? (
          <>
            <Picture src={ph.src} alt={ph.alt} label={ph.label} ratio="3/2" className="object-contain" />
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <DialogTitle className="break-words text-base font-medium">{ph.caption ?? ph.alt}</DialogTitle>
                <DialogDescription className="mt-1 text-sm text-muted">
                  {(index ?? 0) + 1} of {photos.length}
                </DialogDescription>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button variant="outline" size="icon" onClick={() => go(-1)} aria-label="Previous photo">
                  <ChevronLeft className="size-4" aria-hidden="true" />
                </Button>
                <Button variant="outline" size="icon" onClick={() => go(1)} aria-label="Next photo">
                  <ChevronRight className="size-4" aria-hidden="true" />
                </Button>
              </div>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function Tile({ ph, ratio, onOpen, className }: { ph: GalleryPhoto; ratio: Ratio; onOpen: () => void; className?: string }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={`Open photo: ${ph.caption ?? ph.alt}`}
      className={cn(
        "group relative block w-full overflow-hidden rounded-card text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
        className,
      )}
    >
      <Picture src={ph.src} alt={ph.alt} label={ph.label} ratio={ratio} className="h-full transition-transform duration-700 group-hover:scale-105" />
      <span
        aria-hidden="true"
        className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-3 bg-ink/70 px-4 py-3 text-sm text-bg opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-focus-visible:opacity-100"
      >
        <span className="truncate">{ph.caption ?? ph.alt}</span>
        <Expand className="size-4 shrink-0" />
      </span>
    </button>
  );
}

export default function GalleryMasonry({ variant = "masonry", tone, ...rest }: GalleryMasonryProps) {
  const p = withSample(sample, rest);
  const t = tone ?? "plain";
  const [open, setOpen] = React.useState<number | null>(null);
  const strip = React.useRef<HTMLUListElement>(null);

  if (variant === "strip") {
    const move = (d: number) => {
      const el = strip.current;
      if (el) el.scrollBy({ left: d * Math.max(280, el.clientWidth * 0.8), behavior: "smooth" });
    };
    return (
      <Section block="gallery_masonry" variant={variant} tone={t} className="overflow-hidden">
        <Container wide>
          <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <SectionHead title={p.title} intro={p.intro} className="mb-0 sm:mb-0" />
            <div className="flex gap-2">
              <Button variant="outline" size="icon" onClick={() => move(-1)} aria-label="Scroll back">
                <ChevronLeft className="size-4" aria-hidden="true" />
              </Button>
              <Button variant="outline" size="icon" onClick={() => move(1)} aria-label="Scroll on">
                <ChevronRight className="size-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
          <ul
            ref={strip}
            className="-mx-4 mt-10 flex snap-x snap-mandatory gap-5 overflow-x-auto scroll-smooth px-4 pb-4 sm:-mx-6 sm:px-6"
            aria-label={p.title}
          >
            {p.photos.map((ph, i) => (
              <li key={ph.alt + i} className={cn("shrink-0 snap-start", i % 2 ? "w-60 sm:w-72" : "w-72 sm:w-96")}>
                <figure>
                  <Picture src={ph.src} alt={ph.alt} label={ph.label} ratio={i % 2 ? "3/4" : "4/3"} />
                  <figcaption className={cn("mt-3 flex gap-3 text-sm", quiet(t))}>
                    <span className="font-medium tabular-nums text-primary">{String(i + 1).padStart(2, "0")}</span>
                    <span>{ph.caption ?? ph.alt}</span>
                  </figcaption>
                </figure>
              </li>
            ))}
          </ul>
        </Container>
      </Section>
    );
  }

  if (variant === "feature") {
    const five = p.photos.slice(0, 5);
    return (
      <Section block="gallery_masonry" variant={variant} tone={t}>
        <Container>
          <SectionHead title={p.title} intro={p.intro} align="center" />
          <ul className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 lg:grid-rows-2">
            {five.map((ph, i) => (
              <li key={ph.alt + i} className={cn("min-w-0", i === 0 && "col-span-2 lg:row-span-2")}>
                <Tile ph={ph} ratio={i === 0 ? "4/3" : "1/1"} onOpen={() => setOpen(i)} className={cn(i === 0 && "lg:h-full")} />
              </li>
            ))}
          </ul>
          <Lightbox photos={five} index={open} onIndex={setOpen} />
        </Container>
      </Section>
    );
  }

  return (
    <Section block="gallery_masonry" variant={variant} tone={t}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <ul className="columns-2 gap-3 sm:gap-4 lg:columns-3">
          {p.photos.map((ph, i) => (
            <li key={ph.alt + i} className="mb-3 break-inside-avoid sm:mb-4">
              <Tile ph={ph} ratio={ph.ratio ?? "4/3"} onOpen={() => setOpen(i)} />
            </li>
          ))}
        </ul>
        <Lightbox photos={p.photos} index={open} onIndex={setOpen} />
      </Container>
    </Section>
  );
}
