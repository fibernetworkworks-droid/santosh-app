---
name: gst-invoice
description: Raise a GST invoice on her one series, the server's way
---
GOAL: a compliant tax invoice every time, no manual arithmetic.

1. One series: every invoice number comes from HER single running series -
   never invent, never reuse, gaps explained.
2. Party: name, GSTIN (verify the checksum shape), place of supply. B2C
   without GSTIN is fine; B2B without GSTIN is flagged back to her.
3. Lines: HSN/SAC, quantity, rate; discount shown, never folded silently.
4. Tax: CGST+SGST for the same state, IGST for another; round-off only as the
   final line. Compute in code, never in your head.
5. The total is what she charged - if inputs disagree, ASK, do not adjust.
6. Issue + record the same moment the PDF exists (one hidden app row keeps the
   ledger); a cancellation is a credit note, never a deletion.
VERIFY: totals recomputed by code; series sequence continuous; PDF opens.
