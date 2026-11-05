---
name: prog-library-registry
description: Pick libraries from the vetted registry - never a guess
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
2. Jo chahiye woh registry par nahi hai? VERIFY before naming: `pip index versions
   <naam>` ya pypi.org/pypi/<naam>/json through the gated run door - ya saaf keh do:
   "yeh package verify nahi kiya, pehle check karta hoon". NEVER a plausible-sounding
   guess from memory.
3. Install sirf uske tap par (the run door), aur script header mein pin karo jo install
   hua (requests==2.32.3 style) - uski machine reproducible rehti hai.
4. Ek kaam ek library: ek column padhne ke liye pandas mat uthao.
5. Scope note: Hoola's own pylab sandbox runs with NO network - this registry governs
   scripts written for HER PC / her servers, not the sandbox.
NEVER: a package name you have not verified; pip install without her tap; a post-install
script you have not read; a requirements.txt with a name you cannot point to on pypi.org.
