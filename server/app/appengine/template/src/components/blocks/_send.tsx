// v0.999.80 D8 wave 3: one way to send a visitor's details to her website's own enquiry address (the same as the
// contact form: it becomes her lead in Hoola, with the hidden spam trap). Used by the RSVP and question blocks.
import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface Sent {
  ok: boolean;
  said: string;
}

/** POST {name, phone, message, website (spam trap), page} to `endpoint`; without an endpoint (a preview of the kit)
 *  nothing leaves the page and the visitor is told it was noted. */
export function useSend(endpoint?: string) {
  const trap = React.useRef<HTMLInputElement>(null);
  const [busy, setBusy] = React.useState(false);
  const send = async (name: string, phone: string, message: string): Promise<Sent> => {
    if (!endpoint) return { ok: true, said: "Noted (a preview - nothing was sent)." };
    setBusy(true);
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          phone: phone.replace(/\D/g, "").slice(-10),
          message: message.slice(0, 1500),
          website: trap.current?.value || "",
          page: typeof location === "undefined" ? "" : location.pathname,
        }),
      });
      const out = await res.json().catch(() => ({}));
      if (!res.ok || out.ok === false) return { ok: false, said: out.error || "It did not send. Please try again." };
      return { ok: true, said: "Sent" };
    } catch {
      return { ok: false, said: "It did not send - check your connection and try again." };
    } finally {
      setBusy(false);
    }
  };
  const trapField = <input ref={trap} name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />;
  return { send, busy, trapField };
}

/** Name + 10-digit mobile, with the error said under each when the visitor tried to send. */
export function PersonFields({ id, name, phone, setName, setPhone, tried }: {
  id: string;
  name: string;
  phone: string;
  setName: (v: string) => void;
  setPhone: (v: string) => void;
  tried: boolean;
}) {
  const phoneOk = phone.replace(/\D/g, "").length >= 10;
  return (
    <>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-name`}>Your name</Label>
        <Input id={`${id}-name`} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={tried && !name.trim()} />
        {tried && !name.trim() ? <p className="text-sm text-bad">Please add your name.</p> : null}
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-phone`}>Mobile number</Label>
        <Input id={`${id}-phone`} type="tel" inputMode="tel" autoComplete="tel" placeholder="10 digits" value={phone}
          onChange={(e) => setPhone(e.target.value)} aria-invalid={tried && !phoneOk} />
        {tried && !phoneOk ? <p className="text-sm text-bad">A 10-digit mobile number, please.</p> : null}
      </div>
    </>
  );
}

export const personOk = (name: string, phone: string) => !!name.trim() && phone.replace(/\D/g, "").length >= 10;
