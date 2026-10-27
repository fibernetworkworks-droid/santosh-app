"""Build app/bazar/mcp_directory.json.gz from the worldwide MCP master sheet.

    python tools/build_mcp_directory.py path/to/MCP_worldwide_master.xlsx
"""
import gzip
import json
import re
import sys
from pathlib import Path

import openpyxl

SRC = {"npm registry": "npm", "PyPI": "pypi", "awesome-mcp-servers (punkpeye)": "awesome", "awesome-mcp-servers (wong2)": "awesome",
       "best-of-mcp-servers": "best-of", "awesome-mcp-servers (appcypher)": "awesome", "modelcontextprotocol/servers": "reference"}
RISK_FIELDS = {"Security", "Code Execution", "Command Line", "OS Automation", "Cryptography"}
RISK = re.compile(r"\b(crypto|solana|ethereum|bitcoin|defi|wallet|swap|x402|token swap|trad(e|ing)|exploit|pentest|malware|"
                  r"shell command|execute (any|arbitrary)|on-chain|polymarket|betting|private key)\b", re.I)
GUESS = [  # field for rows that came without one (npm / PyPI)
    ("Databases", r"postgres|mysql|sqlite|mongo|redis|database|\bsql\b|clickhouse|supabase|bigquery|snowflake|dynamodb"),
    ("Finance & Fintech", r"stock|trading|payment|invoice|financ|crypto|bank|accounting|tally|zerodha|razorpay|stripe|xero|quickbooks|tax\b"),
    ("Communication", r"slack|e-?mail|gmail|whatsapp|telegram|discord|\bsms\b|twilio|teams\b|chat"),
    ("Search & Data Extraction", r"search|scrap|crawl|extract|serp"),
    ("Knowledge & Memory", r"memory|\brag\b|knowledge|notes?\b|obsidian|notion|vector|embedding"),
    ("Browser Automation", r"browser|playwright|puppeteer|selenium|chrome"),
    ("Cloud Platforms", r"\baws\b|azure|\bgcp\b|kubernetes|k8s|docker|cloudflare|vercel|terraform"),
    ("Developer Tools", r"github|gitlab|\bgit\b|code|lint|\btest|\bapi\b|sdk|\bcli\b|devops|ci/cd|jira|linear"),
    ("Marketing", r"\bseo\b|\bads\b|marketing|analytics|campaign|crm|hubspot|salesforce"),
    ("Location Services", r"\bmaps?\b|geocod|location|weather"),
    ("Travel & Transportation", r"flight|hotel|travel|train|transit|logistic|shipping"),
    ("Social Media", r"twitter|\bx\.com|reddit|youtube|instagram|linkedin|tiktok|facebook"),
    ("Data Science Tools", r"pandas|chart|plot|machine learning|\bml\b|dataset|jupyter"),
    ("Security", r"security|vulnerab|pentest|\bcve\b|firewall"),
    ("Productivity", r"calendar|todo|task|spreadsheet|excel|sheets|docs\b|pdf|word\b|office"),
]
PLACEHOLDER = re.compile(r"^(add your description here|mcp server|a mcp server|an mcp server|test|demo)?\.?$", re.I)


def main(path: str) -> None:
    wb = openpyxl.load_workbook(path, read_only=True)
    rows = list(wb["All MCPs"].iter_rows(values_only=True))[1:]
    out, seen = [], set()
    for r in rows:
        n, src, name, link, field, what, lang, ver, rel, lic, price, official, notes = (list(r) + [None] * 13)[:13]
        if not name or not link or link in seen:
            continue
        seen.add(link)
        what = (what or "").strip()
        notes = str(notes or "")
        repo = ""
        m = re.search(r"repo: (?:git\+)?(\S+)", notes)
        if m:
            repo = re.sub(r"^git://", "https://", m.group(1)).removesuffix(".git")
            repo = re.sub(r"/(issues|wiki|releases|commits/main/?)$", "", repo)
        dl = 0
        m = re.search(r"(\d+) dl/mo", notes)
        if m:
            dl = int(m.group(1))
        f = (field or "").strip()
        if not f:
            hay = f"{name} {what}".lower()
            f = next((label for label, pat in GUESS if re.search(pat, hay)), "Other")
        caution = f in RISK_FIELDS or bool(RISK.search(f"{name} {what}"))
        cloud = bool(price and str(price).startswith("Cloud"))
        out.append([int(n), SRC.get(src, "other"), str(name), str(link), f, "" if PLACEHOLDER.match(what) else what[:400],
                    lang or "", str(ver or ""), str(rel or "")[:10], (lic or "")[:40], "cloud" if cloud else "free",
                    bool(official), repo[:300], dl, caution])
    dest = Path(__file__).resolve().parents[1] / "app" / "bazar" / "mcp_directory.json.gz"
    data = {"source": "Worldwide MCP master: npm, PyPI, awesome-mcp-servers, best-of-mcp-servers, modelcontextprotocol/servers "
                      "(community listings, not individually verified)",
            "columns": ["n", "src", "name", "link", "field", "does", "lang", "version", "released", "licence", "pricing",
                        "official", "repo", "downloads", "caution"],
            "servers": out}
    with gzip.open(dest, "wt", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    print(len(out), "servers ->", dest, dest.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1])
