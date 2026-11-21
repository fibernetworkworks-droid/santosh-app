"use client"; // v0.999.79 D8: the question form needs JavaScript - on a pre-rendered site page it is an island
// v0.999.79 D8 wave 3 block: Discussions - the topics a community talks about (her list), and a question form that
// reaches her (and her team) in Hoola like every enquiry; she answers. Said plainly on the page: visitors do not post
// to each other here (that needs a sign-in, which a website page does not keep).
import * as React from "react";
import { MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Section, Container, SectionHead, type Tone } from "./_kit";
import { PersonFields, personOk, useSend } from "./_send";

export const variants = ["topics"] as const;
export type DiscussionsVariant = (typeof variants)[number];

export interface Topic {
  title: string;
  line?: string;
}

export interface DiscussionsProps {
  variant?: DiscussionsVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  topics?: Topic[];
  endpoint?: string;
  askTitle?: string;
  askNote?: string;
}

export const sample: Required<Omit<DiscussionsProps, "variant" | "tone" | "endpoint">> = {
  title: "What we talk about",
  intro: "Pick a topic or ask your own question; a member replies within a day.",
  topics: [
    { title: "Starting a balcony garden", line: "Pots, soil and what grows in our heat." },
    { title: "Composting at home", line: "Kitchen waste into soil without the smell." },
  ],
  askTitle: "Ask a question",
  askNote: "Your question reaches the organisers; the answer comes to your phone.",
};

export default function Discussions({ variant = "topics", tone, endpoint, ...rest }: DiscussionsProps) {
  const p = { ...sample, ...rest };
  const id = React.useId();
  const { send, busy, trapField } = useSend(endpoint);
  const [name, setName] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [topic, setTopic] = React.useState("");
  const [q, setQ] = React.useState("");
  const [tried, setTried] = React.useState(false);
  const [said, setSaid] = React.useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (!personOk(name, phone) || !q.trim()) return;
    const r = await send(name, phone, `Question${topic ? ` (${topic})` : ""}: ${q.trim()}`);
    setSaid(r.ok ? "" : r.said);
    if (!r.ok) return;
    toast.success("Question sent", { description: "The answer will come to your phone." });
    setQ(""); setTopic(""); setTried(false);
  };

  return (
    <Section block="discussions" variant={variant} tone={tone ?? "plain"}>
      <Container>
        <SectionHead title={p.title} intro={p.intro} />
        <div className="grid gap-10 lg:grid-cols-12">
          <ul className="flex flex-col gap-3 lg:col-span-6">
            {p.topics.map((t) => (
              <li key={t.title}>
                <button type="button" onClick={() => setTopic(t.title)} aria-pressed={topic === t.title}
                  className="flex w-full items-start gap-3 rounded-card border border-line bg-surface p-5 text-left transition-colors hover:border-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary aria-pressed:border-primary">
                  <MessageSquare className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
                  <span className="flex flex-col gap-1">
                    <span className="font-semibold">{t.title}</span>
                    {t.line ? <span className="text-sm text-muted">{t.line}</span> : null}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={submit} noValidate className="grid gap-5 rounded-card border border-line bg-bg p-6 sm:grid-cols-2 lg:col-span-6">
            <h3 className="font-head text-xl font-semibold sm:col-span-2">{p.askTitle}{topic ? <span className="text-primary"> · {topic}</span> : null}</h3>
            <PersonFields id={id} name={name} phone={phone} setName={setName} setPhone={setPhone} tried={tried} />
            <div className="flex flex-col gap-2 sm:col-span-2">
              <Label htmlFor={`${id}-q`}>Your question</Label>
              <Textarea id={`${id}-q`} rows={4} value={q} onChange={(e) => setQ(e.target.value)} aria-invalid={tried && !q.trim()} />
              {tried && !q.trim() ? <p className="text-sm text-bad">Please write your question.</p> : null}
            </div>
            {trapField}
            <div className="flex flex-col gap-2 sm:col-span-2">
              <Button type="submit" disabled={busy}>{busy ? "Sending…" : "Send question"}</Button>
              {said ? <p role="alert" className="text-sm text-bad">{said}</p> : null}
              {p.askNote ? <p className="text-sm text-muted">{p.askNote}</p> : null}
            </div>
          </form>
        </div>
      </Container>
    </Section>
  );
}
