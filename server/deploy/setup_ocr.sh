#!/usr/bin/env bash
# v0.59 Hoola reads photos / scans / bills on the VPS's own CPU: Tesseract + the best models for Indian scripts,
# plus the Python packages for QR codes, PDFs, bills and India facts. Run once on the VPS:
#   bash ~/santosh_app/server/deploy/setup_ocr.sh
set -euo pipefail
CORE=${CORE:-$HOME/apps/santosh-core}
TESS=$CORE/data/tessdata
LANGS="eng hin mar tam tel kan mal ben guj pan ori urd san"

echo "== tesseract binary"
if ! command -v tesseract >/dev/null; then
  sudo apt-get update -y && sudo apt-get install -y tesseract-ocr
fi
tesseract --version | head -1

echo "== tessdata_best models -> $TESS (Apache-2.0)"
mkdir -p "$TESS"
for l in $LANGS osd; do
  f="$TESS/$l.traineddata"
  if [ ! -s "$f" ]; then
    src=tessdata_best; [ "$l" = osd ] && src=tessdata
    curl -fsSL -o "$f.part" "https://raw.githubusercontent.com/tesseract-ocr/$src/main/$l.traineddata" && mv "$f.part" "$f"
    echo "  $l $(du -h "$f" | cut -f1)"
  fi
done
TESSDATA_PREFIX="$TESS" tesseract --list-langs | tail -n +2 | tr '\n' ' '; echo

echo "== python packages"
"$CORE/.venv/bin/pip" install -q "zxing-cpp>=2.2" "pikepdf>=9.0" "pyhanko>=0.25" "imagehash>=4.3" "holidays>=0.60" "invoice2data>=0.4"

echo "== IFSC branch details (razorpay/ifsc, monthly)"
cd "$CORE" && .venv/bin/python -c "from app.india import ifsc; print(ifsc.refresh(), 'bank files')" || true
echo "done: pm2 restart santosh --update-env"
