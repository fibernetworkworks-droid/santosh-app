"""v0.999.316 Build the Web Studio design catalog from a checkout of VoltAgent/awesome-design-md (MIT).

    python tools/designmd_build.py <path to awesome-design-md checkout>

Writes server/app/site/designmd_lib/looks.json.gz (+ LICENSE.txt): every brand folder with a DESIGN.md, under a Hoola
name (never the brand's), its category from the repo's README, a short line with the brand's name taken out, and the
file's own text. Gambling sites are left out. Run it again to refresh; nothing is fetched from the network here.
"""
from __future__ import annotations

import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "app" / "site" / "designmd_lib"
SKIP = {"1win": "a gambling site (casino and sportsbook)"}
NAMES = {
    "airbnb": "Warm marketplace", "airtable": "Colour grid", "aljazeera": "Newsroom", "apple": "Gallery",
    "binance": "Trading floor", "bmw": "Premium drive", "bmw-m": "Track contrast", "bugatti": "Cinema black",
    "cal": "Clean scheduler", "claude": "Warm editorial", "clay": "Soft studio", "clickhouse": "Yellow docs",
    "cohere": "Data gradient", "coinbase": "Trusted blue", "composio": "Plug-in dark", "cursor": "Code night",
    "dell-1996": "Catalogue 1996", "dji": "Product studio", "elevenlabs": "Voice cinema", "expo": "Tight dark",
    "ferrari": "Racing night", "figma": "Playful colour", "framer": "Dark artboard", "hashicorp": "Enterprise clean",
    "hp": "Electric white", "ibm": "Grid system", "intercom": "Friendly blue", "jobright": "Mint pill",
    "kraken": "Violet exchange", "lamborghini": "Black and gold", "linear.app": "Midnight product",
    "lovable": "Friendly gradient", "mastercard": "Cream orbit", "mercury": "Night bank", "meta": "Binary store",
    "minimax": "Neon dark", "miro": "Bright canvas", "mistral.ai": "French minimal", "mintlify": "Reading green",
    "mongodb": "Leaf docs", "mydealz": "Deal feed", "nerdwallet": "Spruce advice", "nike": "Bold sport",
    "nintendo-2001": "Console chrome 2001", "notion": "Calm workspace", "nvidia": "Green energy", "ollama": "Terminal mono",
    "opencode.ai": "Dev terminal", "oracle": "Warm enterprise", "oura": "Paper wellness", "pinterest": "Image wall",
    "playstation": "Game channel", "posthog": "Cream sketchbook", "raycast": "Launcher glow", "renault": "Aurora drive",
    "replicate": "White code", "resend": "Black serif", "revolut": "Dark banking", "runwayml": "Film festival",
    "sanity": "Coral editorial", "sap": "Business frame", "sentry": "Violet monitor", "shopify": "Neon commerce",
    "slack": "Team aubergine", "spacex": "Stark launch", "spotify": "Green beat", "starbucks": "Earth green",
    "stripe": "Indigo finance", "supabase": "Emerald code", "superhuman": "Purple glow", "tesla": "Radical minimal",
    "theverge": "Acid mint", "together.ai": "Blueprint", "uber": "Urban mono", "vercel": "Ink and white",
    "vodafone": "Red chapters", "voltagent": "Void emerald", "warp": "Block terminal", "webflow": "Builder blue",
    "wise": "Bright transfer", "x.ai": "Stark mono", "wired": "Broadsheet", "zapier": "Warm automation",
}
UPPER = {"nike", "ferrari", "vodafone", "bugatti", "lamborghini", "spacex"}
CAT = {"AI & LLM Platforms": "ai", "Developer Tools & IDEs": "dev", "Backend, Database & DevOps": "dev",
       "Productivity & SaaS": "saas", "Design & Creative Tools": "design", "Fintech & Crypto": "fin",
       "E-commerce & Retail": "shop", "Media & Consumer Tech": "consumer", "Automotive": "auto"}


def main(src: str) -> None:
    root = Path(src)
    readme = (root / "README.md").read_text(encoding="utf-8")
    cat_of, line_of, brand_of = {}, {}, {}
    cur = ""
    for ln in readme.split("\n"):
        if ln.startswith("### "):
            h = ln[4:].strip()
            cur = CAT.get(h, "retro" if "Retro" in h else "")
            continue
        m = re.match(r"- \[\*\*(.+?)\*\*\]\(https://getdesign\.md/([^/]+)/design-md\)\s*-\s*(.+)", ln)
        if m and cur:
            brand, slug, desc = m.groups()
            cat_of[slug] = cur
            brand_of[slug] = re.sub(r"\s*\(\d{4}\)", "", brand).replace(".com", "")
            parts = re.split(r"(?<=\.)\s+", desc.strip(), maxsplit=1)
            tail = parts[1] if len(parts) > 1 else parts[0]
            tail = re.split(r"\s+—\s+", tail)[-1]
            for b in {brand_of[slug], brand_of[slug].split()[0]}:
                tail = re.sub(rf"\b{re.escape(b)}\b\s*", "", tail)
            tail = re.sub(r"\s+", " ", tail).strip(" ,.")
            line_of[slug] = (tail[:1].upper() + tail[1:])[:140]
    looks, skipped = [], []
    for d in sorted((root / "design-md").iterdir()):
        f = d / "DESIGN.md"
        if not f.is_file():
            continue
        slug = d.name
        if slug in SKIP:
            skipped.append(f"{slug}: {SKIP[slug]}")
            continue
        if slug not in NAMES:
            raise SystemExit(f"no Hoola name for {slug} - add it to NAMES")
        looks.append({"id": slug.replace(".", "-"), "name": NAMES[slug], "src": slug if "." in slug else slug + ".com",
                      "brand": brand_of.get(slug) or slug.split(".")[0].capitalize(), "cat": cat_of.get(slug, "saas"),
                      "line": line_of.get(slug, ""), "upper": slug in UPPER,
                      "text": f.read_text(encoding="utf-8")})
    try:
        commit = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%h %cs"], capture_output=True,
                                text=True, timeout=10).stdout.strip()
    except Exception:
        commit = ""
    OUT.mkdir(parents=True, exist_ok=True)
    data = {"source": {"repo": "github.com/VoltAgent/awesome-design-md", "licence": "MIT", "commit": commit,
                       "left_out": skipped}, "looks": looks}
    (OUT / "looks.json.gz").write_bytes(gzip.compress(json.dumps(data, ensure_ascii=False).encode(), 9, mtime=0))
    lic = root / "LICENSE"
    if lic.is_file():
        (OUT / "LICENSE.txt").write_text("The DESIGN.md files in looks.json.gz come from github.com/VoltAgent/awesome-design-md"
                                         f" ({commit}).\n\n" + lic.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"{len(looks)} looks written, {len(skipped)} left out", *skipped, sep="\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
