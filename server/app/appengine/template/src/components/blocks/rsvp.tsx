"use client"; // v0.999.82 D8: the form needs JavaScript - on a pre-rendered site page it is an island
// v0.999.82 D8 wave 3 block: RSVP - a guest says yes or no, how many are coming, and a note. With `endpoint` (her
// website's own enquiry address, written by Hoola) it reaches her in Hoola like every enquiry; nothing is stored here.
import * as React from "react";
import { Check, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Section, Container, SectionHead, type Tone } from "./_kit";
import { PersonFields, personOk, useSend } from "./_send";

export const variants = ["card"] as const;
export type RsvpVariant = (typeof variants)[number];

export interface RsvpProps {
  variant?: RsvpVariant;
  tone?: Tone;
  title?: string;
  intro?: string;
  by?: string;
  endpoint?: string;
  maxGuests?: number;
}

export const sample: Required<Omit<RsvpProps, "variant" | "tone" | "endpoint">> = {
  title: "Will you come?",
  intro: "Tell us by the end of November so we can plan the food and the seats.",
  by: "",
  maxGuests: 10,
};

export default function Rsvp({ variant = "card", tone, endpoint, ...rest }: RsvpProps) {
  const p = { ...sample, ...rest };
  const id = React.useId();
  const { send, busy, trapField } = useSend(endpoint);
  const [name, setName] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [coming, setComing] = React.useState("");
  const [guests, setGuests] = React.useState("1");
  const [note, setNote] = React.useState("");
  const [tried, setTried] = React.useState(false);
  const [said, setSaid] = React.useState("");
  const n = Math.min(Math.max(parseInt(guests, 10) || 1, 1), p.maxGuests);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTried(true);
    if (!personOk(name, phone) || !coming) return;
    const msg = `RSVP: ${coming === "yes" ? `coming, ${n} ${n === 1 ? "person" : "people"}` : "cannot come"}` + (note.trim() ? ` - ${note.trim()}` : "");
    const r = await send(name, phone, msg);
    setSaid(r.ok ? "" : r.said);
    if (!r.ok) return;
    toast.success(coming === "yes" ? "See you there" : "Thank you for telling us", { description: `${name.trim()}, your answer has reached the hosts.` });
    setName(""); setPhone(""); setComing(""); setGuests("1"); setNote(""); setTried(false);
  };

  return (
    <Section block="rsvp" variant={variant} tone={tone ?? "surface"}>
      <Container>
        <div className="mx-auto max-w-2xl">
          <SectionHead title={p.title} intro={p.intro} align="center" />
          <form onSubmit={submit} noValidate className="grid gap-5 rounded-card border border-line bg-bg p-6 sm:grid-cols-2 sm:p-8">
            <PersonFields id={id} name={name} phone={phone} setName={setName} setPhone={setPhone} tried={tried} />
            <div className="flex flex-col gap-2 sm:col-span-2">
              <span id={`${id}-coming`} className="text-sm font-medium">Are you coming?</span>
              <ToggleGroup type="single" value={coming} onValueChange={setComing} aria-labelledby={`${id}-coming`} className="justify-start">
                <ToggleGroupItem value="yes" className="gap-2 px-4"><Check className="size-4" aria-hidden="true" />Yes, I will come</ToggleGroupItem>
                <ToggleGroupItem value="no" className="gap-2 px-4"><X className="size-4" aria-hidden="true" />Sorry, I cannot</ToggleGroupItem>
              </ToggleGroup>
              {tried && !coming ? <p className="text-sm text-bad">Please choose one.</p> : null}
            </div>
            {coming === "yes" ? (
              <div className="flex flex-col gap-2">
                <Label htmlFor={`${id}-guests`}>How many of you, with you?</Label>
                <Input id={`${id}-guests`} type="number" inputMode="numeric" min={1} max={p.maxGuests} value={guests} onChange={(e) => setGuests(e.target.value)} />
              </div>
            ) : null}
            <div className="flex flex-col gap-2 sm:col-span-2">
              <Label htmlFor={`${id}-note`}>A note for the hosts (optional)</Label>
              <Textarea id={`${id}-note`} rows={3} value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
            {trapField}
            <div className="flex flex-col gap-2 sm:col-span-2">
              <Button type="submit" size="lg" disabled={busy}>{busy ? "Sending…" : "Send my answer"}</Button>
              {said ? <p role="alert" className="text-sm text-bad">{said}</p> : null}
              {p.by ? <p className="text-center text-sm text-muted">{p.by}</p> : null}
            </div>
          </form>
        </div>
      </Container>
    </Section>
  );
}
