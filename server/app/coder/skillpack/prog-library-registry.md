---
name: prog-library-registry
description: Pick libraries from the vetted registry - never a guess
when_to_use: python library, which library, package, pip install, read excel, read pdf, scrape website, pandas, openpyxl, requests
---
GOAL: every script names only libraries that exist. A hallucinated package name is not a
typo - it is a supply-chain door (typosquatting), so the registry below is the short list
she picks from.

1. Pick from the REGISTRY first:
   - HTTP: requests (sync), httpx (async). Scraping/parsing: beautifulsoup4 + lxml;
     scrapy for big crawls; feedparser for RSS.
   - Excel: openpyxl (xlsx read/write), xlsxwriter (write-heavy), pandas (analysis).
     CSV: stdlib csv, or pandas. PDF: pypdf (merge/split/read), reportlab (write),
     pdfplumber (text + tables).
   - Word: python-docx. PowerPoint: python-pptx. Images: Pillow. Dates: stdlib
     datetime, python-dateutil. QR: qrcode. OCR: pytesseract (needs the tesseract
     binary).
   - Web: flask (small app), fastapi (API). Tests: pytest.
   - Zip, files, paths, email, json, hashing: STDLIB FIRST (zipfile, shutil, pathlib,
     imaplib, smtplib, json, hashlib) - zero supply chain, zero install.
2. What you need is not in the registry? VERIFY before naming: `pip index versions
   <name>` or pypi.org/pypi/<name>/json through the gated run door - or say plainly:
   "I have not verified this package, let me check first". NEVER a plausible-sounding
   guess from memory.
3. Install only on her tap (the run door), and pin what was installed in the script
   header (requests==2.32.3 style) - her machine stays reproducible.
4. One job, one library: do not pull in pandas to read one column.
5. Scope note: Hoola's own pylab sandbox runs with NO network - this registry governs
   scripts written for HER PC / her servers, not the sandbox.
NEVER: a package name you have not verified; pip install without her tap; a post-install
script you have not read; a requirements.txt with a name you cannot point to on pypi.org.
