"""Merge the MCP directory with mcp.so, mcpservers.org and the Apify Store (v0.153).

    python -I tools/merge_mcp_lists.py mcpso_servers.json mcpservers_org_listing.json apify_mcp_servers.json [v1.json.gz]

The v1 base (npm / PyPI / awesome lists) is the file as it was at v0.150.0 (git history); the output is version 2.

Reads the current app/bazar/mcp_directory.json.gz (npm / PyPI / awesome / best-of / reference), adds the three listings,
merges duplicates (same GitHub repo, same package, same name + publisher), and writes the file back with, for EVERY
server: a clean display name, a short description (<= 140 characters), the publisher, a normalised category and the
places its logo can come from (brand site, listing image, GitHub organisation). Junk (mirrors, demos, empty test
packages) is dropped. Apify actors that scrape other people's sites are listed but marked not connectable.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE = DEST = Path(__file__).resolve().parents[1] / "app" / "bazar" / "mcp_directory.json.gz"

# old column positions
N, SRC, NAME, LINK, FIELD, DOES, LANG, VER, REL, LIC, PRICE, OFFICIAL, REPO, DL, CAUTION = range(15)
COLUMNS = ["n", "src", "name", "link", "field", "does", "lang", "version", "released", "licence", "pricing", "official",
           "repo", "downloads", "caution", "title", "short", "by", "logo", "home", "mcp_url", "verified", "featured",
           "users", "aliases", "id", "blocked", "tags", "sources", "pkg", "env"]

CATEGORIES = ["Developer Tools", "AI & Agents", "Search & Web", "Browser Automation", "Databases", "Data & Analytics",
              "Cloud & DevOps", "Security", "Communication", "Productivity", "Knowledge & Memory", "Finance & Payments",
              "Crypto & Web3", "Marketing & SEO", "Social Media", "E-commerce", "Design & Media", "Files & Documents",
              "Maps & Travel", "Health & Science", "Education & Research", "Gaming", "IoT & Hardware", "Business & CRM",
              "Other"]
CAT_MAP = {  # source category (lower case) -> ours; '' = decide from the words
    "developer tools": "Developer Tools", "development": "Developer Tools", "developerapplication": "Developer Tools",
    "version control": "Developer Tools", "coding agents": "Developer Tools", "command line": "Developer Tools",
    "code execution": "Developer Tools", "developer_tools": "Developer Tools",
    "ai & agents": "AI & Agents", "ai": "AI & Agents", "agents": "AI & Agents", "reasoning": "AI & Agents",
    "search": "Search & Web", "search & data extraction": "Search & Web", "web scraping": "Search & Web",
    "news": "Search & Web", "browser automation": "Browser Automation", "automation": "",
    "databases": "Databases", "database": "Databases", "data platforms": "Data & Analytics",
    "data & analytics": "Data & Analytics", "data science tools": "Data & Analytics", "monitoring": "Cloud & DevOps",
    "cloud & infrastructure": "Cloud & DevOps", "cloud platforms": "Cloud & DevOps", "cloud service": "Cloud & DevOps",
    "security": "Security", "communication": "Communication", "productivity": "Productivity",
    "workplace & productivity": "Productivity", "memory & knowledge": "Knowledge & Memory",
    "knowledge & memory": "Knowledge & Memory", "memory": "Knowledge & Memory", "finance & fintech": "Finance & Payments",
    "finance": "Finance & Payments", "finance & commerce": "", "marketing": "Marketing & SEO",
    "seo_tools": "Marketing & SEO", "lead_generation": "Business & CRM", "business": "Business & CRM",
    "social media": "Social Media", "social_media": "Social Media", "ecommerce": "E-commerce",
    "media & design": "Design & Media", "design": "Design & Media", "art & culture": "Design & Media",
    "multimedia process": "Design & Media", "videos": "Design & Media", "files & storage": "Files & Documents",
    "file system": "Files & Documents", "file systems": "Files & Documents", "cloud storage": "Files & Documents",
    "location services": "Maps & Travel", "travel & transportation": "Maps & Travel", "travel": "Maps & Travel",
    "biology, medicine and bioinformatics": "Health & Science", "research": "Education & Research",
    "education": "Education & Research", "gaming": "Gaming", "sports": "Other", "jobs": "Business & CRM",
    "real_estate": "Business & CRM", "integrations": "", "other": "", "other tools and integrations": "",
    "aggregators": "", "community servers": "", "official servers": "", "mcp_servers": "", "os automation": "Developer Tools",
    "cryptography": "Security",
}
GUESS = [  # ours, from the words (first match wins)
    ("Crypto & Web3", r"\b(crypto|blockchain|solana|ethereum|bitcoin|defi|web3|nft|on-?chain|wallet|token swap|evm|base chain)\b"),
    ("Finance & Payments", r"\b(stock|trading|payment|invoice|financ|bank|accounting|tally|zerodha|razorpay|stripe|xero|quickbooks|tax|upi|forex|budget)"),
    ("Databases", r"\b(postgres|mysql|sqlite|mongo|redis|database|sql|clickhouse|supabase|bigquery|snowflake|dynamodb|neo4j|duckdb)"),
    ("Browser Automation", r"\b(browser|playwright|puppeteer|selenium|chrome)"),
    ("Search & Web", r"\b(search|scrap|crawl|extract|serp|web page|news)"),
    ("Communication", r"\b(slack|e-?mail|gmail|whatsapp|telegram|discord|sms|twilio|teams|chat|outlook)"),
    ("Knowledge & Memory", r"\b(memory|rag|knowledge|notes?|obsidian|notion|vector|embedding)"),
    ("Cloud & DevOps", r"\b(aws|azure|gcp|kubernetes|k8s|docker|cloudflare|vercel|terraform|devops|monitor|observab|logs?)\b"),
    ("Security", r"\b(security|vulnerab|pentest|cve|firewall|threat|malware)"),
    ("Marketing & SEO", r"\b(seo|ads|marketing|campaign|newsletter|keyword)"),
    ("Business & CRM", r"\b(crm|hubspot|salesforce|leads?|sales|erp|hr|recruit|jobs?)\b"),
    ("E-commerce", r"\b(shopify|e-?commerce|woocommerce|amazon|product catalog|store|cart)\b"),
    ("Social Media", r"\b(twitter|x\.com|reddit|youtube|instagram|linkedin|tiktok|facebook|bluesky|mastodon)"),
    ("Design & Media", r"\b(figma|design|image|video|audio|music|photo|svg|canva|3d|blender)"),
    ("Files & Documents", r"\b(pdf|file|docx?|excel|spreadsheet|csv|drive|dropbox|s3)\b"),
    ("Maps & Travel", r"\b(maps?|geocod|location|weather|flight|hotel|travel|transit|gis)"),
    ("Health & Science", r"\b(health|medical|clinic|patient|bio|gene|chemistr|pubmed|fhir|drug)"),
    ("Education & Research", r"\b(arxiv|paper|research|learn|course|education|student|academic)"),
    ("Gaming", r"\b(game|minecraft|unity|unreal|roblox|godot|chess)"),
    ("IoT & Hardware", r"\b(iot|home assistant|arduino|raspberry|mqtt|esp32|sensor|smart home|robot)"),
    ("Data & Analytics", r"\b(analytics|chart|dashboard|pandas|dataset|jupyter|metrics|bi)\b"),
    ("Productivity", r"\b(calendar|todo|task|jira|linear|trello|asana|clickup|meeting|time)"),
    ("AI & Agents", r"\b(agent|llm|openai|claude|gemini|prompt|reasoning|thinking|model)"),
    ("Developer Tools", r"\b(github|gitlab|git|code|lint|test|api|sdk|cli|npm|typescript|python|ide)\b"),
]
CAT_NAMES = set(CAT_MAP) | {c.lower() for c in CATEGORIES} | {
    "cloud & infrastructure", "media & design", "developer tools", "ai & agents", "data & analytics", "other"}
RISK = re.compile(r"\b(crypto|solana|ethereum|bitcoin|defi|wallet|swap|x402|trad(e|ing)|exploit|pentest|malware|"
                  r"shell command|execute (any|arbitrary)|on-chain|polymarket|betting|private key)\b", re.I)
SCRAPE = re.compile(r"scrap|crawl|harvest|extractor|leads? (database|list|finder|generator)|\bspider\b|unofficial|"
                    r"no login|bypass", re.I)

CASING = {w.lower(): w for w in (
    "GitHub GitLab Bitbucket PostgreSQL MySQL SQLite MongoDB Redis DynamoDB BigQuery ClickHouse DuckDB Neo4j Supabase "
    "OpenAI ChatGPT Claude Anthropic Gemini YouTube LinkedIn TikTok WhatsApp Telegram Discord Slack Notion Jira Confluence "
    "HubSpot Salesforce Shopify WooCommerce Stripe PayPal Razorpay QuickBooks Xero Zoho AWS GCP Azure Kubernetes Docker "
    "Terraform Cloudflare Vercel Netlify Firebase Figma Canva Airtable Trello Asana ClickUp Zapier n8n Make Gmail Outlook "
    "iOS macOS Android API APIs SDK CLI MCP AI LLM LLMs RAG SQL NoSQL JSON YAML CSV PDF HTML CSS URL URLs HTTP HTTPS SSH FTP "
    "SFTP SMTP IMAP DNS IP VPN CRM ERP SEO SEM SaaS UI UX OCR TTS STT GPT GPU CPU IoT MQTT ESP32 GIS 3D AR VR ID KYC GST "
    "UPI NFT DeFi Web3 EVM JavaScript TypeScript Node.js Python Rust Golang Java Kotlin Swift PHP Ruby Elixir Dart Flutter "
    "React Next.js Vue Svelte Angular Tailwind GraphQL REST gRPC OAuth JWT Playwright Puppeteer Selenium Chrome Firefox "
    "Obsidian Todoist Spotify Reddit Bluesky Mastodon arXiv PubMed FHIR Jupyter Pandas NumPy Grafana Prometheus Datadog "
    "Sentry PagerDuty Elasticsearch OpenSearch Kafka RabbitMQ Snowflake Databricks Splunk Okta Auth0 Twilio SendGrid "
    "Mailchimp Brevo Ahrefs Semrush Moz Perplexity Tavily Brave Exa Firecrawl Apify Bright Data SerpAPI DeepSeek Mistral "
    "Ollama HuggingFace LangChain LlamaIndex Qdrant Pinecone Weaviate Chroma Milvus Linear Monday Miro Webflow WordPress "
    "Wix Squarespace Blender Unity Unreal Godot Roblox Minecraft Home Assistant Raspberry Pi Arduino Xcode VS Code JetBrains "
    "IntelliJ npm PyPI Homebrew AWS Lambda S3 EC2 RDS ECS EKS CloudWatch IAM Kubernetes Helm ArgoCD Jenkins CircleCI "
    "TradingView Binance Coinbase Kraken Uniswap Solana Ethereum Bitcoin Polygon Zerodha Upstox Tally IndiaMART Naukri "
    "Flipkart Amazon Zomato Swiggy Paytm PhonePe ONDC IRCTC DigiLocker Aadhaar PAN BSE NSE SEBI RBI").split()}
HOSTING = re.compile(r"(^|\.)(github\.com|github\.io|githubusercontent\.com|gitlab\.com|npmjs\.com|npmjs\.org|pypi\.org|"
                     r"vercel\.app|netlify\.app|railway\.app|herokuapp\.com|onrender\.com|fly\.dev|pages\.dev|workers\.dev|"
                     r"modal\.run|ngrok\.(io|app|dev)|ngrok-free\.app|smithery\.ai|glama\.ai|mcp\.so|mcpservers\.org|"
                     r"apify\.actor|apify\.com|replit\.(app|dev)|deno\.dev|supabase\.co|azurewebsites\.net|"
                     r"cloudfunctions\.net|run\.app|amazonaws\.com|claude\.com|claude\.ai|example\.(com|org)|localhost|"
                     r"medium\.com|youtube\.com|x\.com|twitter\.com|discord\.(gg|com)|notion\.site|gitbook\.io|"
                     r"readthedocs\.io|huggingface\.co|codeberg\.org|bitbucket\.org|google\.com|linkedin\.com|"
                     r"rapidapi\.com|mintlify\.app|carrd\.co|framer\.(ai|website)|webflow\.io|blogspot\.com)$", re.I)
PLACEHOLDER_URL = re.compile(r"[{}<>$\s]|your[-_]|example|localhost|127\.0\.0\.1|0\.0\.0\.0|<|xxx|placeholder", re.I)
GENERIC_DESC = re.compile(r"^(mirror of|model context protocol servers?|mcp servers?|an? mcp server|mcp|server|test|demo|"
                          r"add your description here|description|todo|tbd|none|null|n/?a|a model context protocol server)\.?$",
                          re.I)
JUNK_NAME = re.compile(r"(^|[-_. /])(demo|test|tests|testing|hello[-_ ]?world|example|examples|sample|template|tutorial|"
                       r"playground|my[-_ ]?first|boilerplate|starter|practice|learning|study|homework|tmp|temp|foo|bar)"
                       r"($|[-_. /])", re.I)
CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍⬀-⯿]")


# ---------------------------------------------------------------------------------------------------------- helpers
def gh_repo(*urls: str | None) -> str:
    for u in urls:
        m = re.search(r"github\.com[/:]([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100})", u or "")
        if m:
            repo = m.group(2).removesuffix(".git")
            if repo.lower() not in ("tree", "blob", "issues", "pulls"):
                return f"{m.group(1)}/{repo}".lower()
    return ""


def domain_of(url: str | None) -> str:
    try:
        host = (urlparse(url or "").hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""
    if not host or "." not in host or HOSTING.search(host) or re.match(r"^\d+(\.\d+){3}$", host):
        return ""
    parts = host.split(".")
    keep = 3 if len(parts) >= 3 and parts[-2] in ("co", "gov", "org", "net", "ac", "nic", "com", "edu", "res") else 2
    return ".".join(parts[-keep:])


def mcp_url_ok(u: str) -> str:
    u = (u or "").strip().rstrip("/.,;)")
    if not u.startswith("https://") or len(u) > 200 or PLACEHOLDER_URL.search(u):
        return ""
    try:
        p = urlparse(u)
    except ValueError:
        return ""
    host = (p.hostname or "").lower()
    if "." not in host or re.search(r"(^|\.)(github\.com|githubusercontent\.com|pypi\.org|npmjs\.com|mcp\.so|"
                                    r"mcpservers\.org|glama\.ai|smithery\.ai|example\.\w+|docs\.\w+)$", host):
        return ""
    if re.search(r"\.(md|html?|png|jpe?g|svg|json|ya?ml|txt|zip|gz)$", p.path, re.I) or "/docs" in p.path.lower():
        return ""
    if not re.search(r"mcp|sse|stream", p.path + host, re.I):
        return ""
    return u.split("#")[0]


def clean_text(t: str | None) -> str:
    t = html.unescape(str(t or ""))
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"<[^>]{0,200}>", " ", t)
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"\([^()]*·[^()]*\)|⏱\s*[\d.]+", " ", t)
    t = EMOJI.sub(" ", t)
    t = re.sub(r"[*_`#>|~]+", " ", t)
    t = unicodedata.normalize("NFKC", t)
    return re.sub(r"\s+", " ", t).strip(" -:;,.—–")


_LEAD = re.compile(
    r"^(this is |this (project|repo|repository|package) (is |provides )?)?(an? |the )?"
    r"((simple|minimal|lightweight|basic|read[- ]only|secure|unified|universal|powerful|comprehensive|production[- ]ready|fast|official|unofficial|"
    r"open[- ]source|typescript|python|node(\.js)?|go|rust|java|local|remote|hosted|community)[ ,-]+){0,3}"
    r"(model context protocol|mcp)( \(mcp\))?( \((stdio|sse|http|streamable[- ]http)\))?( client| server| servers| tool| tools| integration| implementation| bridge| wrapper|"
    r" plugin| adapter| connector| service)+ ?(\(mcp\) )?", re.I)


def short_desc(raw: str | None, title: str) -> str:
    t = clean_text(raw)
    tw = set(re.findall(r"[a-z0-9]+", title.lower())) | {"mcp", "server", "universal", "a", "an", "the", "for", "model",
                                                         "context", "protocol", "tool", "tools", "integration"}
    if t and set(re.findall(r"[a-z0-9]+", t.lower())) <= tw:
        return ""
    if t.lower().rstrip(".") in CAT_NAMES:
        return ""
    if not t or GENERIC_DESC.match(t) or t.lower() in (title.lower(), title.lower() + " mcp"):
        return ""
    m0 = re.match(r"(.{0,80}?\b(?:mcp|model context protocol)\b.{0,40}?)\s+[-–—:]\s+(.{20,})$", t, re.I)
    if m0:
        t = m0.group(2)
    lead_m = _LEAD.match(t)
    ro = bool(lead_m and re.search(r"read[- ]only", lead_m.group(0), re.I))
    rest = _LEAD.sub("", t, count=1).lstrip(" :;,.-–—")
    if rest != t:
        m = re.match(r"(?:that|which|to|for|providing|enabling|allowing|offering)\s+(.*)", rest, re.I)
        if m and rest.lower().startswith("for ") and len(m.group(1)) >= 2:
            t = ("Read-only tools " if ro else "Tools ") + rest
        elif m and len(m.group(1)) > 12:
            body = m.group(1)
            lead = rest.split(" ", 1)[0].lower()
            if lead in ("enabling", "allowing"):
                body = "Lets " + body
            elif lead in ("providing", "offering"):
                body = "Gives " + body
            first = body.split(" ", 1)[0]
            if rest.lower().startswith("for "):
                body = "Tools " + rest   # "for Jira Cloud" / "for executing scripts" -> "Tools for ..."
            elif rest.lower().startswith(("that ", "which ")):
                body = re.sub(r"^(lets|allows|enables|provides|gives|helps)\b", lambda x: x.group(1), body, flags=re.I)
            t = body
        elif len(rest) > 12 and not rest.lower().startswith(("and ", "or ", "with ", "in ", "of ", "& ", "+ ", ", ")):
            t = rest
    t = re.sub(r"\s*\((mcp|model context protocol)\)", "", t, flags=re.I)
    if re.match(r"(?i)for\s", t):
        t = "Tools f" + t[1:]
    t = re.sub(r"(?i)^(an? )?(universal )?mcp (application|app|package|library|lib)\b[:,]?\s*", "", t)
    # first sentence, <= 140 characters, at a word boundary
    m = re.match(r"(.{25,160}?[.!?。])(\s|$)", t)
    if m:
        t = m.group(1)
    if len(t) > 140:
        cut = t[:139].rsplit(" ", 1)[0].rstrip(" ,;:-(")
        t = cut + "…"
    t = t[:1].upper() + t[1:]
    if t and t[-1] not in ".!?…。":
        t += "."
    tw |= {"application", "app", "package", "library"}
    if set(re.findall(r"[a-z0-9]+", t.lower())) <= tw:
        return ""
    return t if len(t) >= 12 else ""


def _case_word(w: str, desc: str) -> str:
    lw = w.lower()
    if lw in CASING:
        return CASING[lw]
    m = re.search(r"\b(" + re.escape(w) + r")\b", desc, re.I) if len(w) > 1 else None
    if m and m.group(1) != m.group(1).lower() and m.group(1) != m.group(1).upper() or (
            m and len(w) <= 4 and m.group(1).isupper()):
        return m.group(1)
    if w.isupper() and len(w) <= 5:
        return w
    return w[:1].upper() + w[1:] if w.islower() else w


def clean_title(raw: str, desc: str = "", slug: bool = False) -> str:
    t = clean_text(raw).strip()
    if not t:
        return ""
    if "/" in t and " " not in t:
        scope, last = t.rsplit("/", 1)
        if re.fullmatch(r"(?i)(mcp|server|mcp[-_]server|mcp[-_]?srv|core|sdk|cli)", last):
            last = scope.rsplit("/", 1)[-1]
        t = last
        scope_name = scope.rsplit("/", 1)[-1].lstrip("@")
    else:
        scope_name = ""
    t = t.lstrip("@")
    t = re.sub(r"^iflow[-_ ]mcp[_-]?|^iflow\s+", "", t, flags=re.I)
    # apify style marketing tails: "X Scraper — No Login, $4/1k", "X | 哔哩哔哩", "X [Download 1M]"
    t = re.sub(r"\s*\[[^\]]*\]", "", t)
    t = re.sub(r"\s*\((?:[^)]*\$[^)]*|unofficial|no login|free|beta|new|official)\)", "", t, flags=re.I)
    for sep in (" — ", " – ", " | ", " :: ", " - "):
        if sep in t and len(t.split(sep, 1)[0]) >= 3:
            t = t.split(sep, 1)[0]
    t = re.sub(r",?\s*\$[\d.,]+\s*/\s*\w+.*$", "", t)
    if slug or (" " not in t and re.search(r"[-_.]", t)) or (" " not in t and t.islower()):
        t = re.sub(r"(?i)^(mcp|server|mcp[-_]server|model[-_]context[-_]protocol)[-_.]+", "", t)
        t = re.sub(r"(?i)[-_.]+(mcp[-_]server|mcp[-_]srv|server[-_]mcp|mcp|server|srv|mcp[-_]ts|mcp[-_]py|ts|py|js|node)$",
                   "", t)
        t = re.sub(r"(?i)[-_.]+(mcp[-_]server|mcp|server)$", "", t)
        t = re.sub(r"(?<!\d)\.|\.(?!\d)|[-_]+", " ", t)
    t = re.sub(r"(?i)\b(model context protocol|mcp servers?|mcp)\b(\s+(server|servers|tool|tools))?", " ", t)
    t = re.sub(r"(?i)^\s*(server|servers)\b|\b(server)\s*$", " ", t)
    t = re.sub(r"(?i)^\s*(for|the|a|an|of)\s+", "", re.sub(r"\s+", " ", t).strip(" -:_.,"))
    t = re.sub(r"(?i)\s+(for|the|a|an|of|and|with|via)$", "", t).strip(" -:_.,()")
    if not t:
        return ""
    if scope_name and t.lower() in ("tools", "tool", "client", "bridge", "api", "plugin", "connector", "agent", "kit",
                                    "registry", "utils", "toolkit", "gateway", "proxy", "remote", "local", "lite"):
        t = scope_name.replace("-", " ").replace("_", " ") + " " + t
    words = re.sub(r"\s+", " ", t).split(" ")
    t = " ".join(_case_word(w, desc) if not CJK.search(w) else w for w in words)
    return t[:60].rstrip()


def apify_image(url: str | None) -> str:
    """Apify images are resized thumbnails (76 px); the original upload is the base64 tail of the address."""
    if not url or "images.apifyusercontent.com" not in url:
        return ""
    tail = url.rsplit("/", 1)[-1].split(".")[0]
    try:
        orig = base64.urlsafe_b64decode(tail + "=" * (-len(tail) % 4)).decode()
    except Exception:
        return ""
    return orig if orig.startswith("https://") and len(orig) < 400 else ""


def guess_cat(*parts: str) -> str:
    hay = " ".join(p for p in parts if p).lower()
    return next((c for c, pat in GUESS if re.search(pat, hay)), "Other")


def map_cat(src_cat: str | None, *words: str) -> str:
    c = CAT_MAP.get((src_cat or "").strip().lower())
    if c:
        return c
    return guess_cat(*words)


def norm_name(t: str) -> str:
    return re.sub(r"[^a-z0-9㐀-鿿]", "", (t or "").lower().replace("mcp", "").replace("server", ""))


_NPM = re.compile(r"^(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]{0,213}$")
_PYPI = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")


def pkg_of(cfg: str) -> list[str]:
    """[kind, name] from a listing's setup config: npx -y <pkg>, uvx <pkg>, docker run ... mcp/<image> (Docker's own MCP
    catalogue only). Placeholders and paths are refused."""
    m = re.search(r'"command"\s*:\s*"npx"\s*,\s*"args"\s*:\s*\[([^\]]*)\]', cfg)
    if m:
        args = re.findall(r'"([^"]*)"', m.group(1))
        names = [a for a in args if not a.startswith("-")]
        if names:
            name = re.sub(r"@(latest|next|\^?[\d.]+[\w.-]*)$", "", names[0])
            if _NPM.match(name):
                return ["npm", name]
    m = re.search(r'"command"\s*:\s*"uvx"\s*,\s*"args"\s*:\s*\[([^\]]*)\]', cfg)
    if m:
        args = [a for a in re.findall(r'"([^"]*)"', m.group(1)) if not a.startswith("-")]
        if args:
            name = re.split(r"[=@<>\[]", args[0])[0]
            if _PYPI.match(name) and name not in ("python", "uv"):
                return ["pypi", name]
    m = re.search(r'"command"\s*:\s*"docker".*?"(mcp/[a-z0-9][a-z0-9._-]{0,80})(?::[\w.-]+)?"', cfg, re.S)
    if m:
        return ["docker", m.group(1)]
    return []


def env_of(cfg: str) -> list[str]:
    m = re.search(r'"env"\s*:\s*\{([^}]*)\}', cfg)
    if not m:
        return []
    return [k for k in re.findall(r'"([A-Z][A-Z0-9_]{2,60})"\s*:', m.group(1)) if k not in ("PATH", "HOME", "NODE_ENV")]


# ---------------------------------------------------------------------------------------------------------- merge
class Entry:
    __slots__ = ("key", "src", "ref", "link", "repo", "cats", "descs", "titles", "by", "lang", "ver", "rel", "lic",
                 "cloud", "official", "dl", "caution", "home", "mcp_url", "verified", "featured", "users", "aliases",
                 "imgs", "tags", "sources", "scraper", "mirror", "apify_endpoint", "pkg", "env")

    def __init__(self, key: str):
        self.key = key
        self.src = ""
        self.ref = self.link = self.repo = self.by = self.lang = self.ver = self.rel = self.lic = ""
        self.home = self.mcp_url = ""
        self.cats: list[tuple[int, str]] = []
        self.descs: list[tuple[int, str]] = []
        self.titles: list[tuple[int, str, bool]] = []
        self.cloud = self.official = self.verified = self.featured = self.caution = self.scraper = self.mirror = False
        self.dl = self.users = 0
        self.aliases: set[str] = set()
        self.imgs: list[str] = []
        self.tags: list[str] = []
        self.sources: set[str] = set()
        self.apify_endpoint = ""
        self.pkg: list[str] = []          # [kind npm | pypi | docker, name] = what the runner box can start
        self.env: list[str] = []          # key / setting names the server reads (from the listings' own setup configs)


def build(so_path: str, org_path: str, ap_path: str) -> dict:
    old = json.load(gzip.open(BASE, "rt", encoding="utf-8"))
    if old.get("version") == 2:
        raise SystemExit("BASE is already merged; pass the v1 file (git show <v0.150 commit>:server/app/bazar/"
                         "mcp_directory.json.gz) as the 4th argument")
    rows = old["servers"]
    entries: dict[str, Entry] = {}
    by_name: dict[tuple[str, str], str] = {}   # (normalised title, publisher) -> key
    by_title: dict[str, list[str]] = {}

    def get(key: str) -> Entry:
        e = entries.get(key)
        if e is None:
            e = entries[key] = Entry(key)
        return e

    # 1. the current directory (npm / PyPI / awesome lists / best-of / reference)
    for r in rows:
        r = (list(r) + [None] * 15)[:15]
        repo = gh_repo(r[REPO], r[LINK]) if r[SRC] not in ("npm", "pypi") or "github.com" in (r[REPO] or "") else ""
        key = ("gh:" + repo) if repo else f"{r[SRC]}:{str(r[NAME]).lower()}"
        e = get(key)
        better = r[SRC] in ("npm", "pypi") and (not e.src or r[DL] > e.dl or e.src not in ("npm", "pypi"))
        if not e.ref or better:
            e.src, e.ref, e.link = r[SRC], str(r[NAME]), str(r[LINK])
            e.lang, e.ver, e.rel, e.lic = r[LANG] or "", r[VER] or "", r[REL] or "", r[LIC] or ""
        e.aliases.add(str(r[NAME]).lower())
        e.repo = e.repo or (f"https://github.com/{repo}" if repo else (r[REPO] or ""))
        e.dl = max(e.dl, int(r[DL] or 0))
        e.cloud |= r[PRICE] == "cloud"
        e.official |= bool(r[OFFICIAL])
        e.caution |= bool(r[CAUTION])
        e.cats.append((2, map_cat(r[FIELD], r[NAME], r[DOES])))
        if r[DOES]:
            e.descs.append((3 if r[SRC] in ("awesome", "reference", "best-of") else 2, r[DOES]))
        e.titles.append((1 if r[SRC] in ("npm", "pypi") else 3, str(r[NAME]), True))
        e.sources.add(r[SRC])
        if r[SRC] in ("npm", "pypi") and (not e.pkg or better):
            e.pkg = [r[SRC], str(r[NAME])]
        if repo:
            e.by = e.by or repo.split("/")[0]
        elif r[SRC] == "npm" and str(r[NAME]).startswith("@"):
            e.by = e.by or str(r[NAME])[1:].split("/")[0]

    # 2. mcp.so
    so = json.load(open(so_path, encoding="utf-8"))["servers"]
    for s in so:
        repo = gh_repo(s.get("github"))
        key = ("gh:" + repo) if repo else "mcpso:" + s["slug"].lower()
        e = get(key)
        if (s.get("author") or "").lower() == "mcp-mirror" or (repo.startswith("mcp-mirror/")):
            e.mirror = True
        if not e.src:
            e.src, e.ref, e.link = "mcpso", (repo or s["slug"]), s.get("url") or ""
            e.lang = s.get("runtime") if s.get("runtime") in ("node", "python", "go", "java", "rust", "c#") else e.lang
        e.repo = e.repo or (f"https://github.com/{repo}" if repo else "")

        e.by = e.by or (repo.split("/")[0] if repo else s.get("author") or "")
        e.titles.append((4, s.get("name") or "", False))
        if s.get("short_description"):
            e.descs.append((2, s["short_description"]))
        e.cats.append((1, map_cat(s.get("category"), s["name"], s.get("short_description") or "", " ".join(s.get("tags") or []))))
        e.tags += [t for t in (s.get("tags") or []) if isinstance(t, str)][:8]
        e.verified |= bool(s.get("verified"))
        e.featured |= bool(s.get("featured"))
        e.home = e.home or (s.get("website") or "")
        logo = s.get("logo") or ""
        if logo.startswith("https://") and "avatars.githubusercontent.com" not in logo:
            e.imgs.append(logo)
        cfg = s.get("config") or ""
        if not e.pkg:
            e.pkg = pkg_of(cfg)
        e.env = sorted(set(e.env) | set(env_of(cfg)))[:8]
        for u in re.findall(r'"(?:url|serverUrl)"\s*:\s*"(https://[^"]+)"', cfg) + \
                re.findall(r'mcp-remote"\s*,\s*"(https://[^"]+)"', cfg):
            if mcp_url_ok(u):
                e.mcp_url = e.mcp_url or mcp_url_ok(u)
        e.sources.add("mcpso")

    # 3. mcpservers.org (the GitHub repo sits inside its logo address when the github field is empty)
    org = json.load(open(org_path, encoding="utf-8"))["servers"]
    for s in org:
        lp = re.search(r"[?&]url=([^&]+)", s.get("logo") or "")
        src_url = unquote(lp.group(1)) if lp else ""
        repo = gh_repo(s.get("github"), src_url)
        key = ("gh:" + repo) if repo else ""
        if not key:
            k2 = by_name.get((norm_name(s["name"]), ""))
            key = k2 or "mso:" + s["slug"].lower()
        e = get(key)
        if repo.startswith("mcp-mirror/"):
            e.mirror = True
        if not e.src:
            e.src, e.ref, e.link = "mso", (repo or s["slug"]), s.get("url") or ""
        e.repo = e.repo or (f"https://github.com/{repo}" if repo else "")

        e.by = e.by or (repo.split("/")[0] if repo else "")
        e.titles.append((5, s.get("name") or "", False))
        if s.get("short_description"):
            e.descs.append((5, s["short_description"]))
        e.cats.append((3, map_cat(s.get("category"), s["name"], s.get("short_description") or "")))
        e.official |= bool(s.get("official"))
        d = domain_of(src_url)
        if d and not e.home:
            e.home = "https://" + d
        text = f"{s.get('readme_excerpt') or ''} {s.get('full_description') or ''}"
        for u in re.findall(r"https://[a-z0-9.-]+\.[a-z]{2,}(?::\d+)?/[^\s\"')<>,]*", text, re.I):
            if mcp_url_ok(u) and not e.mcp_url:
                e.mcp_url = mcp_url_ok(u)
        e.sources.add("mso")

    # 4. Apify Store actors
    ap = json.load(open(ap_path, encoding="utf-8"))["actors"]
    for a in ap:
        if a.get("deprecated"):
            continue
        e = get("apify:" + a["slug"].lower())
        e.src, e.ref, e.link = "apify", a["slug"], a.get("url") or f"https://apify.com/{a['slug']}"
        e.by = a.get("author") or a.get("author_username") or ""

        e.titles.append((5, a.get("name") or "", False))
        e.descs.append((5, a.get("short_description") or ""))
        cats = [c for c in a.get("categories") or [] if c != "MCP_SERVERS"]
        e.cats.append((3, map_cat(cats[0] if cats else "", a["name"], a.get("short_description") or "")))
        e.users = int(a.get("users_30d") or 0)
        e.dl = int(a.get("total_users") or 0)
        e.cloud = True
        e.apify_endpoint = a.get("mcp_endpoint") or ""
        e.mcp_url = mcp_url_ok(e.apify_endpoint) if e.apify_endpoint else ""
        e.scraper = bool(SCRAPE.search(f"{a['name']} {a['slug']} {a.get('short_description') or ''}"))
        img = apify_image(a.get("logo"))
        if img:
            e.imgs.append(img)
        e.sources.add("apify")

    # name + publisher index for duplicates that have no repo in one of the lists
    merged = 0
    for key in list(entries):
        e = entries[key]
        if key.startswith(("mso:", "mcpso:")) and e.titles:
            t = norm_name(max(e.titles, key=lambda x: x[0])[1])
            for k2 in by_title.get(t, []):
                o = entries.get(k2)
                if o is not None and o is not e and not k2.startswith("apify:"):
                    for f in ("descs", "titles", "cats", "imgs", "tags"):
                        getattr(o, f).extend(getattr(e, f))
                    o.aliases |= e.aliases
                    o.sources |= e.sources
                    o.official |= e.official
                    o.verified |= e.verified
                    o.featured |= e.featured
                    o.home = o.home or e.home
                    o.mcp_url = o.mcp_url or e.mcp_url
                    del entries[key]
                    merged += 1
                    break
            else:
                by_title.setdefault(t, []).append(key)
        elif e.titles:
            by_title.setdefault(norm_name(max(e.titles, key=lambda x: x[0])[1]), []).append(key)

    # 5. finish every entry: name, short description, category, logo sources; drop junk
    out, dropped = [], {"mirror": 0, "junk": 0, "no_description": 0}
    seen_ids: set[str] = set()
    for e in entries.values():
        if e.mirror:
            dropped["mirror"] += 1
            continue
        descs = sorted(e.descs, key=lambda x: (-x[0], bool(CJK.search(x[1] or ""))))
        en = [d for p, d in descs if d and not CJK.search(d) and not GENERIC_DESC.match(clean_text(d))]
        long_desc = clean_text(en[0] if en else (descs[0][1] if descs else ""))
        if GENERIC_DESC.match(long_desc):
            long_desc = ""
        titles = sorted(e.titles, key=lambda x: -x[0])
        title = ""
        for _, t, is_slug in titles:
            title = clean_title(t, long_desc, slug=is_slug)
            if title and not (CJK.search(title) and any(not CJK.search(x[1]) for x in titles)):
                break
        if not title:
            title = clean_title(e.ref.rsplit("/", 1)[-1], long_desc, slug=True) or e.ref[:60]
        short = ""
        for p, d in descs:
            if not CJK.search(d or "") or not en:
                short = short_desc(d, title)
                if short:
                    break
        strong = e.official or e.verified or e.featured or e.dl >= 200 or e.users >= 5 or bool(e.mcp_url)
        if JUNK_NAME.search(e.ref) and not strong:
            dropped["junk"] += 1
            continue
        cat = ""
        votes: dict[str, int] = {}
        for p, c in e.cats:
            if c and c != "Other":
                votes[c] = votes.get(c, 0) + p
        cat = max(votes, key=votes.get) if votes else guess_cat(title, long_desc, " ".join(e.tags))
        if not short:
            if not strong:
                dropped["no_description"] += 1
                continue
            short = TEMPLATES.get(cat, "Connects your AI assistant to {t}.").format(t=title)
        caution = e.caution or bool(RISK.search(f"{title} {long_desc}"))
        brand = re.sub(r"[^a-z0-9]", "", title.lower())
        scope = e.ref[1:].split("/")[0].lower().replace("-", "") if e.src == "npm" and e.ref.startswith("@") else ""
        gh_owner = gh_repo(e.repo).split("/")[0].replace("-", "") if e.repo else ""
        if len(brand) >= 3 and brand in (scope, gh_owner, gh_owner.removesuffix("hq"), gh_owner.removesuffix("inc")):
            e.official = True     # published by the brand itself (its own npm scope / GitHub organisation)
        blocked = ""
        if e.src == "apify" and e.scraper:
            blocked = "scraper"
        elif re.search(r"whats\s?app", f"{title} {long_desc}", re.I) and not re.search(
                r"business (platform|api)|cloud api|meta (graph|cloud)", long_desc, re.I):
            blocked = "whatsapp"
        owner = e.repo and gh_repo(e.repo).split("/")[0] or ""
        if owner in ("yourusername", "your-username", "username", "user", "your-org", "yourname", "example", "owner"):
            owner = ""
        if (e.by or "").lower() in ("yourusername", "your-username", "username", "yourname"):
            e.by = ""
        brandish = bool(owner) and (e.official or e.verified or e.featured or any(
            len(w) >= 3 and w in owner.lower().replace("-", "") for w in re.findall(r"[a-z0-9]+", title.lower())))
        dom = domain_of(e.home) or domain_of(e.mcp_url if e.src != "apify" else "")
        logo = [dom, e.imgs[0] if e.imgs else "", owner, 1 if brandish else 0]
        eid = hashlib.sha1(e.key.encode()).hexdigest()[:10]
        if eid in seen_ids:
            continue
        seen_ids.add(eid)
        ref = e.ref if e.src in ("npm", "pypi", "awesome", "reference", "best-of") else (
            gh_repo(e.repo) or e.ref)
        aliases = sorted(a for a in e.aliases if a and a != ref.lower())[:6]
        out.append([0, e.src, ref, e.link or e.repo, cat, "" if long_desc[:len(short) - 1] == short[:-1] else long_desc[:300], e.lang or "", str(e.ver or ""),
                    str(e.rel or "")[:10], (e.lic or "")[:40], "cloud" if (e.cloud or e.mcp_url) else "free", e.official,
                    e.repo[:300], e.dl, caution, title, short, (e.by or owner)[:60], logo, e.home[:200], e.mcp_url,
                    e.verified, e.featured, e.users, aliases, eid, blocked, sorted(set(t.lower() for t in e.tags))[:4], sorted(e.sources), e.pkg, e.env])
    out.sort(key=lambda r: r[15].lower())
    for i, r in enumerate(out, 1):
        r[0] = i
    print("merged by name:", merged, "dropped:", dropped)
    return {"source": "Worldwide MCP directory: npm, PyPI, awesome-mcp-servers, best-of-mcp-servers, "
                      "modelcontextprotocol/servers, mcp.so, mcpservers.org, Apify Store (community listings, "
                      "not individually verified)",
            "version": 2, "columns": COLUMNS, "categories": CATEGORIES, "servers": out}


TEMPLATES = {
    "Databases": "Lets your AI query and manage {t}.", "Developer Tools": "Developer tools for {t}, usable by your AI.",
    "Communication": "Lets your AI read and send through {t}.", "Search & Web": "Lets your AI search and read {t}.",
    "Finance & Payments": "Lets your AI work with {t} money data.", "Productivity": "Lets your AI work in {t}.",
    "Cloud & DevOps": "Lets your AI manage {t} cloud resources.", "Knowledge & Memory": "Gives your AI {t} memory and notes.",
    "Design & Media": "Lets your AI create and edit with {t}.", "Files & Documents": "Lets your AI read and write {t} files.",
}


def main(argv: list[str]) -> None:
    global BASE
    if len(argv) > 3:
        BASE = Path(argv[3])
    data = build(*argv[:3])
    with gzip.open(DEST, "wt", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    print(len(data["servers"]), "servers ->", DEST, DEST.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1:])
