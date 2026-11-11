# HOOLA DOCUMENT KIT — plan (every iLovePDF tool, on Hoola's own server)

Owner, 11 Nov 2026: "NOW LETS WORK ON DOCUMENT HANDLING CAPABILITIES TOOLS :: https://www.ilovepdf.com/ -- go to this
site read all tools. also compare that what hoola existing has ... make a perfect plan that in backend hoola can use
these tools to perform user asked operations ... make a ultimate plan".

**Status:** D0-D5 built, shipped as v0.816.0 (built as 0.794 / 0.795 / 0.805 / 0.806 / 0.814) (owner: 'GO D0 WITH YOUR RECOMMENDATIONS'; decisions D1-D5 taken as recommended in §6). Next: D6.

This plan covers four things:

1. What iLovePDF offers, read from its live pages on 11 Nov 2026.
2. What Hoola already has, read from this repo at v0.792.0.
3. The design: one `pdf_kit` tool and one `server/app/dockit/` engine, running locally on her server with no API key.
4. The phases, the laws, the proof card and the decisions only she can make.

---

## 1. What iLovePDF offers (read from ilovepdf.com, 11 Nov 2026)

The menu has 33 entries. "Extract pages" is a mode inside Split, so there are 32 distinct tools.

| # | Group | Tool | Options seen on the page |
|---|---|---|---|
| 1 | Organize | Merge PDF | order of files |
| 2 | Organize | Split PDF | **Range** (custom / fixed every N / Smart split by document type or a prompt), **Pages** (extract all / select), **Size** (max KB/MB per file, allow compression); "merge all ranges into one" |
| 3 | Organize | Remove pages | – |
| 4 | Organize | Extract pages | (= Split › Pages) |
| 5 | Organize | Organize PDF | sort, delete, add pages |
| 6 | Organize | Scan to PDF | phone camera via QR pairing; orientation, page size (fit / A4 / Letter), margin, merge all |
| 7 | Optimize | Compress PDF | Extreme / Recommended / Less compression |
| 8 | Optimize | Repair PDF | recover a damaged file |
| 9 | Optimize | OCR PDF | Standard / Advanced (50+ languages incl. Hindi, Marathi, Bengali, Tamil, Telugu, Gujarati, Kannada, Malayalam, Punjabi, Oriya, Assamese, Urdu, Sanskrit, Nepali); auto-rotate, deskew, dewarp; output colour original / B&W / grey |
| 10 | To PDF | JPG to PDF | orientation, margins |
| 11 | To PDF | Word to PDF | – |
| 12 | To PDF | PowerPoint to PDF | – |
| 13 | To PDF | Excel to PDF | – |
| 14 | To PDF | HTML to PDF | a URL |
| 15 | From PDF | PDF to JPG | every page, or the embedded images |
| 16 | From PDF | PDF to Word | – |
| 17 | From PDF | PDF to PowerPoint | – |
| 18 | From PDF | PDF to Excel | – |
| 19 | From PDF | PDF to PDF/A | 1b / 1a / 2b / 2u / 2a / 3b / 3u / 3a, allow downgrade |
| 20 | Edit | Rotate PDF | – |
| 21 | Edit | Add page numbers | single / facing pages, cover page, margin, first number, page range, text "{n}", "Page {n} of {p}", custom {n} {p} {r} {rf}; font, size, colour, opacity |
| 22 | Edit | Add watermark | text (font incl. Lohit Devanagari / Marathi, size, colour, shadow, opacity) or image; mosaic; transparency 0/25/50/75; rotation 0/45/90/180/270; page range; over or under the content |
| 23 | Edit | Crop PDF | drag a box; all pages or the current page |
| 24 | Edit | Edit PDF | add or change text, images, shapes, highlights, comments; front / back order |
| 25 | Edit | PDF Forms | detect fields, create a fillable form, fill a form |
| 26 | Security | Unlock PDF | remove the password |
| 27 | Security | Protect PDF | open password; advanced permissions (no print / modify / copy / comment / fill / assemble) |
| 28 | Security | Sign PDF | simple (free) or digital (paid); only me or several people; fields signature / initials / name / date / text / stamp; draw / upload; signing order, expiry, reminders, audit trail, email / SMS validation, QR verification |
| 29 | Security | Redact PDF | smart redact, presets (text / card / phone / email), search, page choice; needs selectable text (OCR first) |
| 30 | Security | Compare PDF | semantic text report or content overlay |
| 31 | Intelligence | AI Summarizer | short / medium / long |
| 32 | Intelligence | Translate PDF | 28 target languages, "keep layout" or "only text" |
| 33 | Intelligence | PDF to Markdown | – |

They also offer **workflows**: several tools chained and saved as one.

Their developer API (iLoveAPI, iloveapi.com) has 24 PDF tools and 2,500 free credits a month. The AI tools are not in
the free tier. PDF to Word, PDF to Excel, PDF to PowerPoint, Crop, Redact and Compare are **not in the API at all**, so
even with their key, six of the tools she sees on the website could not be called from Hoola. Every file sent to their
API leaves her server.

---

## 2. What Hoola already has (v0.792.0, read from the code)

| Area | Where | What it does today |
|---|---|---|
| **`pdf_tools`** | `agent/india_tools.py:12`, engine `app/pdftools.py` (pikepdf) | merge (max 20), pages (pick / reorder "1-3,5"), rotate, smaller (re-saves large images as JPEG), info, verify (pyHanko signature check; trust roots are not checked). Refuses any locked PDF. |
| Make documents | `doc_studio` (`docstudio/`: Chromium HOOLA PRINT + ReportLab fallback), `make_document` (`officegen.py`), `lekhak`, `docs_writer`, `kitab` | designed pdf / docx / xlsx / pptx from her words |
| Read documents | `file_read` (`docread.read_text`: markitdown, pypdf; scanned PDF → `ocr.read_pdf`, **first 5 pages only**), `doc_preview` (page pictures via pypdfium2), `email_attachment do=read` | text out, no file out |
| Edit Word / Excel | `doc_desk` (`docdesk.py` `edit_docx` / `edit_xlsx`) | real edits, saved on her Haan. A PDF "edit" is re-printed as plain text, so the layout is lost. |
| Images | `image_edit` (`imgedit/`) | crop, scan filter, redact by blur, watermark, compress to a KB target. Images only, never a PDF. |
| Translate / summarise | `lekhak translate`, `notebook_*`, `kitab`, `notary` | the output is a new document; the original layout is not kept |
| Compare | `contracts redline` (Word tracked changes), `sheet_milaan` (spreadsheets) | no PDF compare |
| Sign | `pdf_tools verify` only; `lekhak sign_request` / `contracts esign` make a card only | nothing is ever signed |
| Office → PDF | `net/media.office_to_pdf` through an optional Gotenberg container (`gotenberg_url`, empty by default) | a preview only; no deploy script installs it |
| Sandbox | `pylab` | could script anything, but is not a product door |

Plumbing that already works and will be reused as is:

- **Files in:** `chatfiles.store` (25 MB cap, magika type check) → `PcFile` row. A tool reads the bytes with `make_tools._owner_bytes(ctx, file_id)`.
- **Files out:** `make_tools._deliver(ctx, name, data, source)` → `pc_file` card (phone + console) + signed expiring link (`pc/service.download_path`).
- **Retention:** every file is deleted after 24 h (`pc_file_hours`).

Libraries and binaries:

- **In requirements:** pypdf, pypdfium2, pikepdf, pyhanko, reportlab, uharfbuzz, Pillow, python-docx, python-pptx, openpyxl, markitdown, pytesseract, playwright, magika.
- **Already on her VPS:** tesseract with tessdata_best for 13 Indian languages (`deploy/setup_ocr.sh`), and Chromium.
- **Not set up anywhere:** LibreOffice, ocrmypdf, Ghostscript, veraPDF, pdfplumber.

### The gap, tool by tool

| iLovePDF tool | Hoola today | After this plan |
|---|---|---|
| Merge | ✅ `pdf_tools merge` | ✅ + bookmarks per file, any count, mixed inputs (images / Office in the same merge) |
| Split | ❌ (`pages` makes one subset only) | ✅ ranges / every N / each page / by size / by bookmarks / by blank pages / smart |
| Remove / extract pages | ⚠️ via `pages` | ✅ named actions |
| Organize | ⚠️ reorder only | ✅ reorder, delete, duplicate, insert blank, insert from another PDF, reverse, interleave (front/back scans) |
| Scan to PDF | ❌ | ✅ phone photos → flatten (imgedit `scan`) → A4 → one PDF → OCR |
| Compress | ⚠️ re-saves images only | ✅ 3 levels + **a target size** ("under 200 KB for the exam portal"), checked after |
| Repair | ❌ | ✅ qpdf recovery (inside pikepdf) → page re-render as a last resort, with a report of what came back |
| OCR | ⚠️ text out, 5 pages | ✅ a **searchable PDF** (invisible text layer), every page, 13 Indian languages + English, deskew / rotate |
| JPG to PDF | ❌ | ✅ orientation, page size, margin, one or many |
| Word / PPT / Excel to PDF | ❌ (preview only) | ✅ LibreOffice headless on her server |
| HTML to PDF | ⚠️ inside doc_studio | ✅ any URL through the scrape lane's SSRF guard + Chromium |
| PDF to JPG / PNG | ❌ | ✅ every page at a chosen dpi, or the embedded images as they are |
| PDF to Word | ❌ | ✅ editable docx (text + headings + tables + pictures), fidelity said honestly |
| PDF to Excel | ❌ | ✅ tables → xlsx, numbers as numbers, column totals checked |
| PDF to PowerPoint | ❌ | ✅ a slide per page (page picture + its text in the notes) |
| PDF to Markdown | ⚠️ via file_read | ✅ a .md file out |
| PDF/A | ❌ | ✅ PDF/A-2b / 3b, **validated** (veraPDF) before it is called PDF/A |
| Rotate | ✅ | ✅ + auto-rotate by text direction (Tesseract OSD) |
| Page numbers | ❌ | ✅ every iLovePDF option + Devanagari digits + Bates numbering for legal work |
| Watermark | ❌ (images only) | ✅ text (Hindi / English) or her logo, mosaic, opacity, rotation, over / under, pages |
| Header / footer | ❌ | ✅ (iLovePDF does not have it) |
| Crop | ❌ | ✅ a box, or auto-trim white margins |
| Edit PDF | ❌ | ✅ add text / image / shape / highlight / note. Changing EXISTING text in place is limited, and said so. |
| Forms | ❌ | ✅ detect fields, fill (from her words, a sheet row or her Pehchaan Locker), flatten, create a fillable form |
| Unlock | ❌ refused | ✅ restrictions removed without a password; an open password typed only in a sealed box, never in chat |
| Protect | ❌ | ✅ AES-256 + permissions; the password never in chat (§4.4) |
| Sign | ❌ (verify only) | ✅ her drawn / uploaded signature placed + a real digital signature (pyHanko); signing requests to others with an audit trail |
| Redact | ❌ | ✅ **true** redaction (the text is gone, checked by re-reading), with Indian presets (Aadhaar, PAN, phone, card, bank account, email, GSTIN) |
| Compare | ❌ | ✅ text report + a highlighted overlay PDF |
| Summarise / translate | ⚠️ in other tools, layout lost | ✅ summary / Q&A routed to the existing brains; translate with layout kept (text placed back in its own boxes, overflow flagged) |
| Workflows | ❌ | ✅ a chain of steps in one call, saved as "my workflow", runnable on a batch |
| Batch | ❌ | ✅ one action on many files, results in a ZIP |
| — | — | **Hoola extras:** metadata edit / clean, sanitize (remove JavaScript / attachments / hidden data), extract attachments, bookmarks, N-up / booklet printing, flatten annotations, grayscale, "fit to A4", Kruti Dev → Unicode (already in lekhak) |

---

## 3. The design

### 3.1 One tool, one engine

This follows the `image_edit` / `audio_edit` / `video_kit` pattern: one tool the model learns once, with a single action
enum. The model sends parameters; the code does the work.

- **NEW tool `pdf_kit`** in `agent/pdfkit_tools.py`, family `pdfkit`. The registry goes from 625 to 626, and the 21 test files that pin `len(TOOLS) == 625` move with it.
- **NEW engine `server/app/dockit/`**, one file per group:

| File | Group | Actions |
|---|---|---|
| `organize.py` | Organize | merge, split, remove, extract, organize (reorder / duplicate / blank / insert / reverse / interleave), nup, booklet |
| `optimize.py` | Optimize | compress (level / target_kb), repair, linearize, grayscale |
| `ocr.py` | OCR | searchable layer (ocrmypdf if installed, else our own: Tesseract hOCR → invisible text with ReportLab, merged per page with pikepdf), auto-rotate, deskew |
| `convert.py` | Convert | to_pdf (images / office / html / text / md), from_pdf (jpg / png / images / docx / xlsx / pptx / md / txt), pdfa + validate |
| `stamp.py` | Overlays | page_numbers, watermark, header_footer, bates. ReportLab overlay merged under / over each page with pikepdf; fonts from `indicpdf` so Devanagari joins correctly. |
| `edit.py` | Edit | crop / autocrop, add text / image / shape / highlight / note, metadata, bookmarks, flatten, sanitize, attachments |
| `forms.py` | Forms | detect, fill, flatten, create |
| `secure.py` | Security | protect, unlock, redact |
| `sign.py` | Signing | place signature, digital sign (pyHanko), verify (moved from `pdftools.verify`) |
| `compare.py` | Compare | text diff (pypdfium2 text + difflib, paragraph-aware) + visual overlay (render both, Pillow pixel diff, changes boxed in red) |
| `smart.py` | AI | summarize / ask / translate_layout / smart_split; the only part that calls a model, metered via `usage.run_meter` |
| `flow.py` | Workflows | steps = [...] chains, saved workflows, batch → zip |
| `check.py` | Verification | the "is the output what she asked for" law (§4.1) |
| `api.py` | HTTP | `/api/pdfkit/*` for the console page and the phone screen (§3.4) |

- **`pdf_tools` stays** as a thin alias over the same engine. Old tool-card asks, voice routes and prompts keep working, and nothing is broken by a rename. Its description points to `pdf_kit` for anything more.
- **Routing fix** (a live bug): admit.py:755-760 sends "lock / password / unlock / watermark" asks to `pdf_tools`, which cannot do any of them. They now go to `pdfkit`. `prompts.py:134 / :305` are updated the same way.

### 3.2 The call shape

```
pdf_kit(action="split", file_id="...", mode="every", every=5)
pdf_kit(action="compress", file_id="...", target_kb=200)
pdf_kit(action="watermark", file_ids=[...], text="CONFIDENTIAL", opacity=0.25, rotation=45, layer="over")
pdf_kit(action="redact", file_id="...", presets=["aadhaar","pan","phone"], find=["Ramesh Kumar"])
pdf_kit(action="convert", file_id="...", to="xlsx")
pdf_kit(action="flow", file_ids=[...], steps=[{"action":"merge"},{"action":"page_numbers","text":"Page {n} of {p}"},
                                            {"action":"compress","target_kb":900},{"action":"protect"}])
```

- **Pages:** one grammar everywhere, reusing `pdftools.pages_from` and extending it with `odd`, `even`, `last`, `-1` and `all-but-last`.
- **Inputs:** every input is a `file_id` (a chat file, an email attachment already stored, a Drive file via `drive.service.fetch`, or the output of an earlier step).
- **Outputs:** one `pc_file` card each, or a ZIP for batches and splits of more than 10 files. Each result says pages, size before and after, what changed, and what was checked.

### 3.3 Engines: local first, no key

| Job | Engine | Licence | On her VPS? |
|---|---|---|---|
| structure, encrypt, crop, merge, repair | **pikepdf** (libqpdf) | MPL-2.0 | ✅ |
| render pages, text with positions | **pypdfium2** | Apache / BSD | ✅ |
| forms, simple reads | **pypdf** | BSD | ✅ |
| overlays, new pages, invisible OCR text | **ReportLab** + indicpdf fonts | BSD | ✅ |
| images | **Pillow** | HPND | ✅ |
| OCR | **Tesseract** + tessdata_best (13 Indian langs) | Apache-2.0 | ✅ |
| HTML → PDF | **Chromium** (Playwright) | BSD | ✅ |
| digital signatures | **pyHanko** | MIT | ✅ |
| Office ↔ PDF | **LibreOffice headless** (`soffice --convert-to`) | MPL-2.0 | ❌ → `deploy/setup_docs.sh` |
| searchable PDF, deskew, PDF/A | **ocrmypdf** | MPL-2.0 | ❌ → setup_docs.sh (our own Tesseract path works without it) |
| PDF tables → Excel | **pdfplumber** | MIT | ❌ → requirements |
| PDF/A validation | **veraPDF** (Java CLI) | MPL-2.0 / GPL dual | ❌ → setup_docs.sh, optional |
| strong compression, PDF/A conversion | **Ghostscript** | **AGPL-3.0** | ❌ — owner decision D2 |
| ~~PyMuPDF / fitz~~ | — | AGPL-3.0 | **not used** (pypdfium2 + pikepdf cover it) |
| ~~pdf2docx~~ | — | GPL-3.0 | **not used**; our own PDF → Word is built on pypdfium2 + pdfplumber + python-docx |

- **No engine installed** → the action says so plainly and names the one line that installs it (the `video_kit` / `lab_check` habit). Nothing is faked.
- **iLoveAPI is optional**, behind owner decision D1. It is a BYOK fallback (`ILOVEAPI_PUBLIC_KEY` in the VPS `.env` only), off by default, used only for an action the local engine refused, and it names itself on the card ("made by iLoveAPI; your file was sent to them").

### 3.4 Surfaces

- **Chat and voice:** `pdf_kit` sits in the chat tool set. On a call it is reached through `santosh_kaam` (`VOICE_VIA_KAAM`), never declared to Gemini Live. "Is PDF ko 200 KB ka karo" works on a call, and the file card lands in the chat.
- **Console page `/console/documents`** (`static/console/dockit.js`, a "Documents" sidebar row): the grid of every tool in the iLovePDF grouping, so she recognises it. A drop zone, a per-tool options panel (the same options as the table in §1), page thumbnails to tick, reorder or rotate by drag (pypdfium2 thumbnails via `/api/pdfkit/thumbs`), a before / after preview, the result card, and "Ask Hoola" beside it. The page calls the same engine the chat uses; one brain, no second path.
- **Phone:** a Documents screen with the same grid, plus Scan to PDF (multi-photo capture → `scan` filter → PDF → OCR). It reuses the existing attach + `pc_file` card.

---

## 4. The laws (each enforced in code, each with a test)

### 4.1 Done = checked

After every action, `check.py` opens the output and proves the result before the card says done:

| Action | What is checked |
|---|---|
| any | opens with pikepdf, and the page count is the one expected |
| split | page counts add up |
| compress | output is smaller; a target_kb is met, or the card says the smallest it reached |
| ocr | text now extracts from every page that had none |
| redact | **every found string is gone** when the page is re-read |
| protect | the file will not open without the password; restricted permissions read back as set |
| pdfa | veraPDF passes, or the card says "PDF/A not validated" and never claims compliance |
| convert to docx / xlsx | the file opens; an xlsx column total equals the source table's total |
| sign | pyHanko validates its own signature |
| translate_layout | no box overflowed, or each overflow is listed |

A failed check means a failure card with the reason. It never means "ho gaya".

### 4.2 The original is never touched

Every action makes a NEW file. The original stays as it was.

### 4.3 Redaction is real or it is not called redaction

- **How:** the matched glyph boxes come from pypdfium2. Those pages are re-drawn as images at 300 dpi with black boxes burned in, then OCR'd back so the rest stays searchable. The text and images under each box leave the file, and metadata and hidden layers are stripped.
- **Presets:** Aadhaar (12 digits with the Verhoeff check), PAN, phone, email, card (Luhn check), IFSC + account number, GSTIN (check digit), vehicle number, PIN code. All are by pattern and checksum, never guessed.
- **Before it runs:** she sees the boxes on a preview and confirms, because it cannot be undone on that copy.
- **Scanned PDFs:** OCR first, said on the card.
- **Overlays:** a black rectangle drawn over text is **never** offered as redaction; that is the classic leak.

### 4.4 Passwords never travel in chat (the non-negotiable rule)

- **Protect:** Hoola generates a strong password and shows it **only on her card**, never to the model and never in history or logs. Or she types her own into a sealed field on the card or the console page (the v0.397 Systems pattern).
- **Unlock:**
  - A PDF that opens but carries restrictions (owner password only): pikepdf removes them with no password. This is allowed only for her own file.
  - A PDF with an open password: the password goes in the sealed field only, and is used once and forgotten.
  - Hoola never asks for a password in chat, and never tries to crack one.
- **Bank / Aadhaar statements:** their known password formats (e.g. name + DOB) are typed by HER in the sealed field; Hoola never "guesses from her details".

### 4.5 Only her files

- A file_id must belong to her tenant (`_owner_bytes` already checks).
- Unlock, protect-removal and redaction-removal are refused on a file that came from another avatar or a customer.

### 4.6 Content is data, never instructions

Text inside a PDF (including form-field values, JavaScript and hidden text) is never obeyed. Sanitize strips JavaScript, launch actions and embedded files by default, and they are named on the card.

### 4.7 Size and time are capped, refused before the run, never silently cut

| Limit | Default | Setting |
|---|---|---|
| file size | 200 MB | `dockit_max_mb` |
| pages per file | 2,000 | — |
| OCR pages per call | 300 | — |
| time | 10 min, process-group kill | — |
| runs at once | 2 heavy runs (LibreOffice / OCR / render) at nice 19 | — |

A bigger job runs in the background like the research runs (worker slot, resumable), and the card says "N of M pages".

### 4.8 Signing is honest about what it is

| What she gets | What it means legally |
|---|---|
| A placed signature (her drawn or uploaded image) | an **electronic** signature (IT Act s.3A), not a digital one |
| A pyHanko signature with Hoola's document certificate | proves "unchanged since Hoola signed it", not her legal identity |
| A Class 3 DSC (on a USB token; cannot be used from the server) or **Aadhaar eSign** through a licensed ESP | a **legally valid digital signature** — owner decision D4 |

The card always names which of these she got.

---

## 5. Phases

Each phase ships as its own version with tests, following the usual ritual.

### D0 — setup + the proof card (1 version)

- `deploy/setup_docs.sh`: libreoffice-core / writer / calc / impress (nogui), ocrmypdf, pdfplumber, default-jre-headless + veraPDF (optional), the fonts LibreOffice needs for Indian scripts (fonts-noto-core, fonts-lohit-*).
- vps-ops jobs `docs_setup` and `docs_check`. `python -m app.dockit check` prints every engine as LIVE / MISSING with the measured time of one real conversion.
- `app/quality/pdfcard.py`: about 40 fixture PDFs, all generated in code, so no real person's data is used:
  - text, scanned (pictures of text), Hindi, a table invoice, a form, a signed file, a broken file, a locked file, a 300-page file, an image-heavy file.
  - Every action is run on them and scored in code by the §4.1 checks.
  - `python -m app.quality pdf`, plus vps-ops `pdf_card`. This card is the yardstick for every phase.

### D1 — Organize + Optimize + simple Convert (pure local, no new binary)

- **Actions:** merge (+ bookmarks, images in the same merge), split (all modes except smart), remove, extract, organize, rotate (+ auto via OSD), compress (low / recommended / extreme + target_kb), repair, images → PDF, PDF → jpg / png / images, PDF → md / txt, info.
- **Wiring:** the `pdf_kit` tool, `pdf_tools` as an alias, the routing fix, prompts, labels, tool-card asks. A voice route through santosh_kaam.

### D2 — Edit + stamps

- **Actions:** page numbers (every iLovePDF option + Devanagari digits + Bates), watermark (text / logo, mosaic, under / over), header / footer, crop + autocrop, add text / image / shape / highlight / note, metadata edit / clean, bookmarks, flatten, N-up, booklet, grayscale, fit to A4, sanitize, extract attachments.

### D3 — Security

- protect (AES-256, permissions, sealed password per §4.4)
- unlock (restrictions; sealed open password)
- true redaction with Indian presets + the preview confirm (§4.3)

### D4 — OCR + Office + PDF/A

- searchable PDF on every page in 14 languages
- Word / Excel / PowerPoint / HTML / text → PDF
- PDF → Word (reflowed: headings by font size, paragraphs, tables via pdfplumber, pictures in place)
- PDF → Excel (tables, numbers typed, totals checked)
- PDF → PowerPoint
- PDF/A-2b / 3b + validation

Fidelity for PDF → Word is graded on the card as "editable copy, layout approximate". It is never sold as "exactly like the original".

### D5 — Forms + Sign

- **Forms:** detect fields, fill (from her words, a sheet row for a batch of 500 forms, or masked Pehchaan Locker references the same way the PC operator types them), flatten, create a fillable form from a plain PDF (the model proposes fields, she confirms).
- **Sign:** place her signature (drawn on the phone / console canvas, or uploaded; kept sealed per tenant), pyHanko digital sign, verify with trust roots.
- **Signing requests:** to other people via a signed link page `/sign/<token>`:
  - their OTP by email (official mail) or SMS (her DLT template);
  - an audit trail page appended to the PDF;
  - reminders and expiry.
- **Aadhaar eSign:** only after decision D4.

### D6 — Compare + AI

- **compare:** text report + highlighted overlay PDF + "what changed in money / dates / names" pulled out by code first, the model only phrasing it.
- **summarize / ask:** routed to the existing notebook / lekhak brains with page citations [p.N].
- **translate_layout:** every text block translated (one model call per page, numbers and names checked by code like the hub translate), then placed back in its own box with fit-to-box font size and Devanagari / Tamil fonts. Overflow is listed. "Only text" mode = a Lekhak document.
- **smart_split:** the model names the boundaries ("invoice 1 ends p.3"), code splits there, and she sees the split list before the files are made.

### D7 — Workflows + batch + surfaces

- **Workflows:** `flow` chains, saved workflows ("CA ke liye: merge → numbers → compress 5 MB → protect"), batch on many files → ZIP.
- **Console page** `/console/documents` and the **phone Documents screen** + Scan to PDF.
- **Delivery and size:** results to Drive / email on her tap; the 24 h file life is said on every card. Big uploads come via a Drive link to get past the 25 MB chat cap.

### D8 — Optional fallback (only on D1 = yes)

- **iLoveAPI BYOK:** used only after the local engine refused, named on the card, metered in credits, with a monthly cap.

---

## 6. Decisions only she can make

| # | Decision | My recommendation |
|---|---|---|
| D1 | May files go to iLoveAPI (a third party) as a fallback? | **No by default.** Everything here runs locally. Turn it on later only for a named action, if the proof card shows a real local gap. |
| D2 | Install Ghostscript (AGPL-3.0, run as a separate program on our server)? | **Not at first.** pikepdf + Pillow re-encoding does the compression, and ocrmypdf's PDF/A needs it only for some files. Revisit if the card shows compression falling short. |
| D3 | Protect passwords: Hoola-generated (shown once on her card) or typed by her in a sealed field? | **Both**, generated as the default. |
| D4 | Legally valid digital signatures: integrate an Aadhaar eSign provider (eMudhra / NSDL / Protean ESP — paid per sign, needs an agreement)? | **Plan it, build after D5**, once she picks a provider and signs their agreement. |
| D5 | Raise the 25 MB chat upload limit for documents? | **Keep 25 MB** in chat, and take bigger files via a Drive link (no new upload path to secure). |

---

## 7. What this plan does NOT do, and why

- **Crack or guess passwords:** never. It is the non-negotiable rule and the law.
- **Remove a watermark** or a DRM restriction from someone else's document: refused. The same stand `image_edit` takes on watermark removal.
- **Fake a government seal, stamp or signature:** refused. Stamps are her own company stamp image only.
- **Edit existing text in place pixel-perfectly:** PDF text is placed glyph by glyph, so no free tool does this faithfully. Hoola offers "white out + rewrite in the same box" with the font matched as near as it can, and says "approximate" on the card.
- **Use PyMuPDF / pdf2docx:** AGPL / GPL, kept out of the tree on purpose.

---

## 8. Verified vs not

- **Verified (this session):**
  - the iLovePDF tool list and options, read from their live pages;
  - Hoola's existing tools, files, libraries and routing, read from the code;
  - the 625-tool pin in 21 test files;
  - LibreOffice / ocrmypdf / Ghostscript / veraPDF absent from every deploy script.
- **Not verified:**
  - the tool pages for Remove / Repair / Organize / Merge / Unlock / Forms / PDF to Markdown (taken from the home page grid only);
  - iLoveAPI's exact pricing per tool;
  - whether her VPS has the disk for LibreOffice (~600 MB) + a JRE (~200 MB) for veraPDF. D0's `docs_check` measures it before anything installs.
