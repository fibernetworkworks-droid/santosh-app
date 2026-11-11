#!/usr/bin/env bash
# v0.794 HOOLA DOCUMENT KIT (docs/DOCUMENT_KIT_PLAN.md D0): the engines pdf_kit uses, on the VPS's own CPU.
# Idempotent. Python packages install into the santosh venv here; the system programs need sudo, which the deploy
# user does not have - so this script PRINTS the one apt line for the owner to paste in the DigitalOcean console,
# then re-run vps-ops > docs_setup (or docs_check) to see them LIVE.
#   bash ~/santosh_app/server/deploy/setup_docs.sh
set -uo pipefail
CORE=${CORE:-$HOME/apps/santosh-core}
PIP="$CORE/.venv/bin/pip"

echo "== python packages (pikepdf MPL-2.0, pypdfium2 Apache/BSD, pypdf BSD, reportlab BSD, pdfplumber MIT, pyhanko MIT)"
"$PIP" install -q "pikepdf>=9.0" "pypdfium2>=4.30" "pypdf>=4" "reportlab>=4.0" "pdfplumber>=0.11" "pyhanko>=0.25" 2>&1 | tail -3

echo "== system programs"
missing=""
command -v soffice >/dev/null || command -v libreoffice >/dev/null || missing="$missing libreoffice-core libreoffice-writer libreoffice-calc libreoffice-impress fonts-noto-core fonts-lohit-deva"
command -v tesseract >/dev/null || missing="$missing tesseract-ocr"
command -v ocrmypdf >/dev/null || missing="$missing ocrmypdf"
command -v java >/dev/null || missing="$missing default-jre-headless"
if [ -n "$missing" ]; then
  echo "NOT INSTALLED:$missing"
  echo "OWNER: paste this ONE line in the DigitalOcean console (Droplet > Console), then re-run vps-ops > docs_check:"
  echo "  sudo apt-get update && sudo apt-get install -y --no-install-recommends$missing"
  echo "(LibreOffice ~600 MB = Word / Excel / PowerPoint -> PDF; ocrmypdf = searchable PDFs later; Ghostscript is NOT"
  echo " installed on purpose - AGPL, owner decision D2.)"
else
  echo "all system programs present"
fi
df -h "$CORE" | tail -1 | awk '{print "disk free on the core volume: " $4}'

echo "== Hoola OCR models (13 Indian languages) come from setup_ocr.sh"
[ -d "$CORE/data/tessdata" ] && ls "$CORE/data/tessdata" | sed 's/.traineddata//' | tr '\n' ' ' && echo || echo "not yet: bash ~/santosh_app/server/deploy/setup_ocr.sh"

echo "== engine check"
cd "$CORE" && timeout 600 .venv/bin/python -m app.dockit check
