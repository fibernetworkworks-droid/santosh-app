"""Image editing for Hoola (one tool, `image_edit`), built in two honest layers.

LOCAL (ops.py): deterministic Pillow / numpy edits that need no key and no network - resize to a social size, crop, rotate,
brightness / contrast / colour, filters, document-scan look, redaction, borders, text and watermark, convert, compress to a
target size, collage, plain enlargement. The same input and the same steps give the same bytes.

AI (ai.py): the edits a model has to do - background removal, true upscaling, object removal, background replacement,
restyle, old-photo restore, colourise, "change X". Each routes to the first engine that is really set up (local rembg,
Gemini through photogen, then the BYOK zoo gateways) and says which one ran. No engine = a plain sentence saying what to
set; it never pretends.

run.py joins the two into one pipeline; the tool in agent/imgedit_tools.py resolves her files and delivers the result.
Every output is re-encoded, so camera EXIF / GPS never travels with an edited picture."""
