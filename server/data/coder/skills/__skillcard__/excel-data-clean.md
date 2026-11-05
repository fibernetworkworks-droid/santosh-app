---
name: excel-data-clean
description: Clean an Indian leads sheet: phones, dupes, consent
---
GOAL: a sheet safe to message from.

1. Normalise phones to +91XXXXXXXXXX: strip spaces/dashes, fix 0/91 prefixes,
   10-digit-only rows stay. A number that cannot be repaired is marked bad,
   never guessed.
2. Deduplicate on the NORMALISED number (and on name+number); keep the row
   with more filled fields, say how many went.
3. Consent: find the opt-in column (opt_in / consent / permission...). Only
   'yes/1/true/haan' counts. Missing column = the whole sheet is unsent until
   she answers.
4. Names: trim, title-case, obvious honorifics kept as given.
5. Report back: total, clean, duplicates removed, bad numbers, consented -
   four numbers, then ask whether to proceed.
NEVER: invent a number, drop a column, message from an unconsented sheet.
