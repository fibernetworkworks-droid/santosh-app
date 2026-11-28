import { QRCodeSVG } from "qrcode.react";
import { cn } from "@/lib/utils";

/**
 * A QR code drawn as SVG, always black on white (what phone scanners read best) (no picture service, nothing leaves the page).
 * For a UPI payment use upiLink(): <QrCode value={upiLink({ pa: "shop@upi", pn: "Sharma Sweets", am: 250 })} label="Scan to pay" />
 */
export function QrCode({ value, size = 168, label, className }: { value: string; size?: number; label?: string; className?: string }) {
  return (
    <figure className={cn("inline-flex flex-col items-center gap-2", className)}>
      <div className="rounded-card border border-line bg-surface p-3">{/* always black on white: phone scanners read that best */}
        <QRCodeSVG value={value} size={size} level="M" bgColor="white" fgColor="black" title={label ? undefined : "QR code"} />
      </div>
      {label && <figcaption className="text-sm text-muted">{label}</figcaption>}
    </figure>
  );
}

/** A UPI payment link (upi://pay) for a QR code or a "Pay with UPI" button. `am` is in rupees; `tn` is the note. */
export function upiLink({ pa, pn, am, tn, cu = "INR" }: { pa: string; pn: string; am?: number; tn?: string; cu?: string }) {
  const q = new URLSearchParams({ pa, pn, cu });
  if (am !== undefined && am > 0) q.set("am", am.toFixed(2));
  if (tn) q.set("tn", tn.slice(0, 80));
  return `upi://pay?${q.toString()}`;
}
