import * as React from "react";
import { Download } from "lucide-react";
import { Button, type ButtonProps } from "@/components/ui/button";

/**
 * A button that makes a PDF in the browser (invoices, receipts, certificates, tickets) and saves it. The PDF maker
 * (@react-pdf/renderer) is loaded only when the button is pressed, so pages stay light. `document` builds the PDF from
 * react-pdf's own parts, which the function receives:
 *   <PdfButton fileName={`invoice-${o.number}.pdf`} document={({ Document, Page, Text, View, StyleSheet }) => {
 *     const s = StyleSheet.create({ page: { padding: 32 }, h: { fontSize: 18, marginBottom: 12 } });
 *     return <Document><Page size="A4" style={s.page}><Text style={s.h}>Invoice {o.number}</Text></Page></Document>;
 *   }}>Download invoice</PdfButton>
 * Colours inside a PDF are plain values (a PDF cannot read the app's tokens): use the theme's colours from useTheme().
 */
export type PdfParts = typeof import("@react-pdf/renderer");

export function PdfButton({
  document,
  fileName = "document.pdf",
  children = "Download PDF",
  ...props
}: Omit<ButtonProps, "onClick" | "children"> & {
  document: (parts: PdfParts) => React.ReactElement;
  fileName?: string;
  children?: React.ReactNode;
}) {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  async function make() {
    setBusy(true);
    setError("");
    try {
      const parts = await import("@react-pdf/renderer");
      const blob = await parts.pdf(document(parts) as never).toBlob();
      const url = URL.createObjectURL(blob);
      const a = window.document.createElement("a");
      a.href = url;
      a.download = fileName.endsWith(".pdf") ? fileName : `${fileName}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e) {
      console.error("The PDF could not be made", e);
      setError("The PDF could not be made. Try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <span className="inline-flex flex-col gap-1">
      <Button type="button" onClick={make} disabled={busy || props.disabled} {...props}>
        <Download className="h-4 w-4" aria-hidden />
        {busy ? "Making the PDF…" : children}
      </Button>
      {error && <span role="alert" className="text-sm text-bad">{error}</span>}
    </span>
  );
}
