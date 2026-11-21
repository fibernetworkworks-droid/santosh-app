"use client"; // v0.999.82 D8: playing needs JavaScript - on a pre-rendered site page it is an island
// v0.999.82 D8 wave 3 block: Game area - a small game made from HER words, played on the page: "memory" (find the
// pairs of her words) or "scramble" (unscramble her words). The shuffles come from a seed, so the page drawn on the
// server and in the browser is the same; "Play again" shuffles anew. A game not in this list is written specially.
import * as React from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Section, Container, SectionHead, type Tone } from "./_kit";

export const variants = ["play"] as const;
export type GameAreaVariant = (typeof variants)[number];
export const games = ["memory", "scramble"] as const;
export type GameKind = (typeof games)[number];

export interface GameAreaProps {
  variant?: GameAreaVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  game?: GameKind;
  words?: string[];
}

export const sample: Required<Omit<GameAreaProps, "variant" | "tone">> = {
  title: "A quick game",
  intro: "Turn two cards at a time and find the pairs.",
  game: "memory",
  words: ["Mango", "Jasmine", "Peacock", "Lotus"],
};

/** a small seeded shuffle: the same seed gives the same order on the server and in the browser */
function shuffle<T>(xs: T[], seed: number): T[] {
  const a = [...xs];
  let s = seed || 1;
  for (let i = a.length - 1; i > 0; i--) {
    s = (s * 16807) % 2147483647;
    const j = s % (i + 1);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function Memory({ words, seed, again }: { words: string[]; seed: number; again: () => void }) {
  const cards = React.useMemo(() => shuffle(words.flatMap((w) => [w, w]), seed), [words, seed]);
  const [open, setOpen] = React.useState<number[]>([]);
  const [found, setFound] = React.useState<string[]>([]);
  const [turns, setTurns] = React.useState(0);
  const flip = (i: number) => {
    if (open.length === 2 || open.includes(i) || found.includes(cards[i])) return;
    const now = [...open, i];
    setOpen(now);
    if (now.length === 2) {
      setTurns((t) => t + 1);
      if (cards[now[0]] === cards[now[1]]) { setFound((f) => [...f, cards[i]]); setOpen([]); }
      else window.setTimeout(() => setOpen([]), 800);
    }
  };
  const won = found.length === words.length;
  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm tabular-nums text-muted" aria-live="polite">{won ? `All pairs found in ${turns} turns.` : `${found.length} of ${words.length} pairs · ${turns} turns`}</p>
      <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4">
        {cards.map((w, i) => {
          const shown = open.includes(i) || found.includes(w);
          return (
            <li key={i}>
              <button type="button" onClick={() => flip(i)} aria-label={shown ? w : `Card ${i + 1}, face down`}
                className={cn("flex aspect-4/3 w-full items-center justify-center rounded-card border p-2 text-center text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary sm:text-base",
                  shown ? "border-primary bg-primary/10 text-ink" : "border-line bg-primary text-primary-ink hover:bg-primary/90",
                  found.includes(w) && "border-ok bg-ok/10")}>
                {shown ? w : "?"}
              </button>
            </li>
          );
        })}
      </ul>
      {won ? <Button variant="secondary" onClick={again} className="w-fit"><RotateCcw className="size-4" aria-hidden="true" />Play again</Button> : null}
    </div>
  );
}

function Scramble({ words, seed, again }: { words: string[]; seed: number; again: () => void }) {
  const order = React.useMemo(() => shuffle(words, seed), [words, seed]);
  const [at, setAt] = React.useState(0);
  const [guess, setGuess] = React.useState("");
  const [right, setRight] = React.useState(0);
  const [said, setSaid] = React.useState("");
  const id = React.useId();
  if (at >= order.length) {
    return (
      <div className="flex flex-col items-start gap-4">
        <p className="font-head text-3xl font-semibold tabular-nums">{right} / {order.length}</p>
        <Button variant="secondary" onClick={again}><RotateCcw className="size-4" aria-hidden="true" />Play again</Button>
      </div>
    );
  }
  const w = order[at];
  let mixed = shuffle(w.split(""), seed + at + 7).join("");
  if (mixed === w && w.length > 1) mixed = w.slice(1) + w[0];
  const check = (e: React.FormEvent) => {
    e.preventDefault();
    const ok = guess.trim().toLowerCase() === w.toLowerCase();
    if (ok) setRight((r) => r + 1);
    setSaid(ok ? "Right." : `It was: ${w}.`);
    setGuess("");
    setAt((a) => a + 1);
  };
  return (
    <form onSubmit={check} className="flex flex-col gap-4">
      <p className="text-sm tabular-nums text-muted">Word {at + 1} of {order.length}</p>
      <p className="font-head text-4xl font-semibold uppercase tracking-widest text-primary" aria-label={`Letters: ${mixed.split("").join(" ")}`}>{mixed}</p>
      <label htmlFor={id} className="text-sm font-medium">Your answer</label>
      <div className="flex gap-3">
        <Input id={id} value={guess} onChange={(e) => setGuess(e.target.value)} autoComplete="off" className="max-w-xs" />
        <Button type="submit">Check</Button>
      </div>
      {said ? <p aria-live="polite" className="text-muted">{said}</p> : null}
    </form>
  );
}

export default function GameArea({ variant = "play", tone, ...rest }: GameAreaProps) {
  const p = { ...sample, ...rest };
  const game: GameKind = (games as readonly string[]).includes(p.game) ? p.game : "memory";
  const words = Array.from(new Set(p.words.map((w) => w.trim()).filter(Boolean))).slice(0, game === "memory" ? 8 : 12);
  const [seed, setSeed] = React.useState(7);
  return (
    <Section block="game_area" variant={variant} tone={tone ?? "surface"}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <div className="max-w-3xl rounded-card border border-line bg-bg p-6 sm:p-8">
          {game === "memory" ? (
            <Memory key={seed} words={words} seed={seed} again={() => setSeed((s) => s + 1)} />
          ) : (
            <Scramble key={seed} words={words} seed={seed} again={() => setSeed((s) => s + 1)} />
          )}
        </div>
      </Container>
    </Section>
  );
}
