// Board screen (signed-in portal): work as cards in workflow columns, moved with buttons (keyboard friendly).
import * as React from "react";
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Plus, Flag } from "lucide-react";
import { Section, Container, type Tone } from "./_kit";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";

export const variants = ["columns", "lanes", "compact"] as const;
export type ScreenBoardVariant = (typeof variants)[number];

export type Priority = "High" | "Normal" | "Low";

export interface BoardCard {
  id: string;
  title: string;
  who: string;
  due: string;
  priority: Priority;
  /** index into `columns` */
  column: number;
}

export interface ScreenBoardProps {
  variant?: ScreenBoardVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  columns?: string[];
  cards?: BoardCard[];
}

export const sample: Required<Omit<ScreenBoardProps, "variant" | "tone">> = {
  title: "Work board",
  intro: "Every job, from new to done. Move a card when its step is finished.",
  columns: ["New", "In progress", "Waiting on customer", "Done"],
  cards: [
    { id: "J-214", title: "Kitchen repair quote, Kothrud", who: "Vikram Shetty", due: "Today", priority: "High", column: 0 },
    { id: "J-215", title: "Bulk order for Sana Traders", who: "Anjali Mehta", due: "Fri", priority: "Normal", column: 0 },
    { id: "J-216", title: "Website photos for the Diwali menu", who: "Farah Khan", due: "Mon", priority: "Low", column: 0 },
    { id: "J-209", title: "Install water purifier, Baner", who: "Vikram Shetty", due: "Today", priority: "High", column: 1 },
    { id: "J-210", title: "October GST invoices", who: "Anjali Mehta", due: "Tomorrow", priority: "Normal", column: 1 },
    { id: "J-205", title: "Site visit report for Mehta Stores", who: "Farah Khan", due: "Wed", priority: "Normal", column: 2 },
    { id: "J-207", title: "Replacement part for Priya Nair", who: "Vikram Shetty", due: "Thu", priority: "Low", column: 2 },
    { id: "J-198", title: "Annual service, Kaveri Foods", who: "Anjali Mehta", due: "Done 18 Nov", priority: "Normal", column: 3 },
    { id: "J-201", title: "Refund for order ORD-1031", who: "Farah Khan", due: "Done 17 Nov", priority: "Low", column: 3 },
  ],
};

const PRIORITY_CLS: Record<Priority, string> = {
  High: "text-bad",
  Normal: "text-warn",
  Low: "text-muted",
};

function initials(name: string) {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function useBoard(cards: BoardCard[], columns: string[]) {
  const [list, setList] = React.useState(cards);
  const [said, setSaid] = React.useState("");
  const [lastMoved, setLastMoved] = React.useState<string | null>(null);
  function move(id: string, by: -1 | 1) {
    const c = list.find((x) => x.id === id);
    if (!c) return;
    const column = Math.min(columns.length - 1, Math.max(0, c.column + by));
    if (column === c.column) return;
    setList((l) => l.map((x) => (x.id === id ? { ...x, column } : x)));
    setLastMoved(id);
    setSaid(`${c.title} moved to ${columns[column]}`);
    if (column === columns.length - 1) toast.success(`Moved to ${columns[column]}`, { description: c.title });
  }
  function add(title: string, who: string) {
    const n = Math.max(0, ...list.map((c) => Number(c.id.replace(/\D/g, "")) || 0)) + 1;
    const card: BoardCard = { id: `J-${n}`, title, who, due: "No date", priority: "Normal", column: 0 };
    setList((l) => [card, ...l]);
    setLastMoved(card.id);
    setSaid(`${title} added to ${columns[0]}`);
  }
  return { list, move, add, said, lastMoved };
}

type B = ReturnType<typeof useBoard>;

function Head({ title, intro, sampleShown, children }: { title: string; intro: string; sampleShown: boolean; children?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <div className="flex items-center gap-3">
          <h2 className="font-head text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
          {sampleShown ? <Badge tone="outline">Sample</Badge> : null}
        </div>
        <p className="mt-1 text-sm text-muted">{intro}</p>
      </div>
      {children}
    </div>
  );
}

function MoveButtons({ b, c, columns }: { b: B; c: BoardCard; columns: string[] }) {
  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon-sm"
        className="size-10 sm:size-8"
        disabled={c.column === 0}
        aria-label={c.column > 0 ? `Move "${c.title}" back to ${columns[c.column - 1]}` : `"${c.title}" is in the first column`}
        onClick={() => b.move(c.id, -1)}
      >
        <ChevronLeft className="size-4" />
      </Button>
      <Button
        variant="ghost"
        size="icon-sm"
        className="size-10 sm:size-8"
        disabled={c.column === columns.length - 1}
        aria-label={c.column < columns.length - 1 ? `Move "${c.title}" on to ${columns[c.column + 1]}` : `"${c.title}" is done`}
        onClick={() => b.move(c.id, 1)}
      >
        <ChevronRight className="size-4" />
      </Button>
    </div>
  );
}

function CardItem({ b, c, columns, showWho = true, dense }: { b: B; c: BoardCard; columns: string[]; showWho?: boolean; dense?: boolean }) {
  const done = c.column === columns.length - 1;
  return (
    <li
      className={cn(
        "flex flex-col gap-3 rounded-card border border-line bg-surface shadow-card transition-colors hover:border-ink/20",
        dense ? "p-3" : "p-4",
        b.lastMoved === c.id ? "animate-fade-in" : "",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className={cn("text-sm font-medium leading-snug", done ? "text-muted line-through decoration-line" : "")}>{c.title}</h4>
        <span className="shrink-0 text-xs tabular-nums text-muted">{c.id}</span>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          {showWho ? (
            <span className="flex min-w-0 items-center gap-1.5" title={c.who}>
              <Avatar className="size-6 shrink-0">
                <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">{initials(c.who)}</AvatarFallback>
              </Avatar>
              <span className="truncate">{c.who.split(" ")[0]}</span>
            </span>
          ) : null}
          <span className="flex shrink-0 items-center gap-1">
            <CalendarIcon className="size-3.5" aria-hidden="true" />
            {c.due}
          </span>
          <span className={cn("flex shrink-0 items-center gap-1", PRIORITY_CLS[c.priority])}>
            <Flag className="size-3.5" aria-hidden="true" />
            {c.priority}
          </span>
        </div>
        <MoveButtons b={b} c={c} columns={columns} />
      </div>
    </li>
  );
}

function Live({ b }: { b: B }) {
  return (
    <p className="sr-only" aria-live="polite">
      {b.said}
    </p>
  );
}

function AddCard({ b, who }: { b: B; who: string }) {
  const [text, setText] = React.useState("");
  const [hint, setHint] = React.useState("");
  const id = React.useId();
  return (
    <form
      className="flex flex-wrap gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const t = text.trim();
        if (!t) {
          setHint("Type a card title first.");
          return;
        }
        b.add(t, who);
        setText("");
        setHint("");
      }}
    >
      <label htmlFor={id} className="sr-only">
        New card title
      </label>
      <Input
        id={id}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          if (hint && e.target.value.trim()) setHint("");
        }}
        placeholder="Add a card..."
        className="h-10 min-w-0 flex-1 bg-surface"
        aria-invalid={hint ? true : undefined}
        aria-describedby={hint ? `${id}-hint` : undefined}
      />
      {/* the add button stays enabled: pressing it on an empty title says what to do (UX rule: no pre-disabled submit) */}
      <Button type="submit" size="icon" variant="secondary" aria-label="Add card">
        <Plus className="size-4" />
      </Button>
      {hint && (
        <p id={`${id}-hint`} role="alert" className="w-full text-xs text-bad">
          {hint}
        </p>
      )}
    </form>
  );
}

export default function ScreenBoard({ variant = "columns", tone, ...rest }: ScreenBoardProps) {
  const d = { ...sample, ...rest };
  const sampleShown = rest.cards === undefined;
  const b = useBoard(d.cards, d.columns);
  const people = Array.from(new Set(b.list.map((c) => c.who)));

  if (variant === "lanes") {
    return (
      <Section block="screen_board" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <Head title={d.title} intro={d.intro} sampleShown={sampleShown} />
          <Live b={b} />
          <div className="overflow-x-auto rounded-card border border-line bg-surface">
            <div className="min-w-6xl">
              <div className="flex border-b border-line text-sm font-medium">
                <div className="w-44 shrink-0 px-4 py-3 text-muted">Who</div>
                {d.columns.map((col, i) => (
                  <div key={col} className="min-w-0 flex-1 border-l border-line px-4 py-3">
                    {col} <span className="ml-1 tabular-nums text-muted">{b.list.filter((c) => c.column === i).length}</span>
                  </div>
                ))}
              </div>
              {people.map((p) => (
                <div key={p} className="flex border-b border-line last:border-b-0">
                  <div className="flex w-44 shrink-0 items-start gap-2 px-4 py-4">
                    <Avatar className="size-8 shrink-0">
                      <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">{initials(p)}</AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-medium">{p}</h3>
                      <p className="text-xs text-muted">
                        {b.list.filter((c) => c.who === p && c.column < d.columns.length - 1).length} open
                      </p>
                    </div>
                  </div>
                  {d.columns.map((col, i) => (
                    <ul key={col} aria-label={`${p}, ${col}`} className="flex min-w-0 flex-1 flex-col gap-2 border-l border-line bg-bg/60 p-2">
                      {b.list
                        .filter((c) => c.who === p && c.column === i)
                        .map((c) => (
                          <CardItem key={c.id} b={b} c={c} columns={d.columns} showWho={false} dense />
                        ))}
                    </ul>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </Container>
      </Section>
    );
  }

  if (variant === "compact") {
    return (
      <Section block="screen_board" variant={variant} tone={tone ?? "plain"} tight>
        <Container wide>
          <Head title={d.title} intro={d.intro} sampleShown={sampleShown}>
            <p className="text-sm text-muted">
              <span className="font-medium tabular-nums text-ink">{b.list.filter((c) => c.column < d.columns.length - 1).length}</span> open ·{" "}
              <span className="font-medium tabular-nums text-ink">{b.list.filter((c) => c.priority === "High" && c.column < d.columns.length - 1).length}</span>{" "}
              high priority
            </p>
          </Head>
          <Live b={b} />
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {d.columns.map((col, i) => {
              const inCol = b.list.filter((c) => c.column === i);
              return (
                <section key={col} aria-label={col} className="flex min-w-0 flex-col gap-2 rounded-card bg-ink/5 p-2">
                  <div className="flex items-center justify-between px-2 pt-1">
                    <h3 className="text-sm font-semibold">{col}</h3>
                    <span className="rounded-full bg-surface px-2 py-0.5 text-xs font-medium tabular-nums text-muted">{inCol.length}</span>
                  </div>
                  {i === 0 ? <AddCard b={b} who={people[0] ?? "You"} /> : null}
                  <ul className="flex flex-col gap-2">
                    {inCol.map((c) => (
                      <CardItem key={c.id} b={b} c={c} columns={d.columns} dense />
                    ))}
                  </ul>
                  {inCol.length === 0 ? <p className="px-2 py-4 text-center text-xs text-muted">Nothing here</p> : null}
                </section>
              );
            })}
          </div>
        </Container>
      </Section>
    );
  }

  return (
    <Section block="screen_board" variant={variant} tone={tone ?? "plain"} tight>
      <Container wide>
        <Head title={d.title} intro={d.intro} sampleShown={sampleShown}>
          <Button
            onClick={() => {
              b.add("New job", people[0] ?? "You");
              toast.success("Card added to " + d.columns[0]);
            }}
          >
            <Plus className="size-4" aria-hidden="true" />
            New card
          </Button>
        </Head>
        <Live b={b} />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {d.columns.map((col, i) => {
            const inCol = b.list.filter((c) => c.column === i);
            return (
              <section key={col} aria-label={col} className="flex min-w-0 flex-col gap-3">
                <div className="flex items-center gap-2 border-b border-line pb-2">
                  <span aria-hidden="true" className={cn("size-2 rounded-full", i === d.columns.length - 1 ? "bg-ok" : i === 0 ? "bg-primary" : "bg-warn")} />
                  <h3 className="text-sm font-semibold">{col}</h3>
                  <span className="text-sm tabular-nums text-muted">{inCol.length}</span>
                </div>
                <ul className="flex flex-col gap-3">
                  {inCol.map((c) => (
                    <CardItem key={c.id} b={b} c={c} columns={d.columns} />
                  ))}
                </ul>
                {inCol.length === 0 ? (
                  <p className="rounded-card border border-dashed border-line px-4 py-8 text-center text-sm text-muted">No cards yet</p>
                ) : null}
              </section>
            );
          })}
        </div>
      </Container>
    </Section>
  );
}
