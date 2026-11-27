"""Build server/app/route/n8nlib_index.json.gz from a checkout of github.com/Zie619/n8n-workflows at the fixed commit.

    git clone https://github.com/Zie619/n8n-workflows /tmp/n8nw && git -C /tmp/n8nw checkout f8639776c97c05e9730c2ec5c97163d76f6d2290
    cd server && python -m tools.n8nlib_build /tmp/n8nw

Each workflow is run through Hoola's own importer (route/n8n.py) and checked by the route engine's checks, so the
index says honestly how much of it Hoola can do. Files that are not workflows or that the checks refuse are left out.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import dhara_tools as D  # noqa: E402
from app.route import n8n as N, n8nlib as L  # noqa: E402

NICE = {"googleSheets": "Google Sheets", "googleDrive": "Google Drive", "googleCalendar": "Google Calendar",
        "gmail": "Gmail", "httpRequest": "Web request", "openAi": "OpenAI", "youTube": "YouTube", "github": "GitHub",
        "hubspot": "HubSpot", "wordpress": "WordPress", "postgres": "Postgres", "mySql": "MySQL", "emailSend": "Email",
        "emailReadImap": "Email (IMAP)", "microsoftOutlook": "Outlook", "linkedIn": "LinkedIn", "whatsApp": "WhatsApp",
        "openWeatherMap": "OpenWeatherMap", "rssFeedRead": "RSS", "twitter": "X (Twitter)", "mongoDb": "MongoDB",
        "awsS3": "AWS S3", "googleDocs": "Google Docs", "clickUp": "ClickUp", "typeform": "Typeform",
        "lmChatOpenAi": "OpenAI", "lmChatGoogleGemini": "Google Gemini", "lmChatAnthropic": "Anthropic"}
CORE = {"manualTrigger", "start", "scheduleTrigger", "cron", "interval", "webhook", "set", "if", "switch", "filter",
        "merge", "noOp", "stickyNote", "code", "function", "functionItem", "wait", "splitInBatches", "splitOut",
        "aggregate", "summarize", "sort", "limit", "removeDuplicates", "respondToWebhook", "stopAndError",
        "executeWorkflow", "executeWorkflowTrigger", "errorTrigger", "dateTime", "itemLists", "html", "markdown",
        "xml", "crypto", "renameKeys", "compareDatasets", "convertToFile", "extractFromFile", "spreadsheetFile",
        "formTrigger", "chatTrigger", "form", "moveBinaryData", "readBinaryFile", "writeBinaryFile", "readWriteFile",
        "agent", "chainLlm", "chainSummarization", "informationExtractor", "textClassifier", "sentimentAnalysis",
        "chainRetrievalQa", "outputParserStructured", "memoryBufferWindow", "toolWorkflow", "toolCode",
        "toolHttpRequest", "embeddingsOpenAi", "textSplitterRecursiveCharacterTextSplitter",
        "documentDefaultDataLoader", "n8n", "executeCommand", "ssh", "mcpTrigger"}


def nice(t: str) -> str:
    t = re.sub(r"(Trigger|Tool)$", "", t)
    if t in NICE:
        return NICE[t]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t[:1].upper() + t[1:])


def describe(doc: dict) -> str:
    for n in doc.get("nodes") or []:
        if str(n.get("type", "")).endswith("stickyNote"):
            c = str((n.get("parameters") or {}).get("content") or "")
            c = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", c)
            c = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", c)
            c = re.sub(r"[#*_`>|~=-]+", " ", c)
            c = re.sub(r"\s+", " ", c).strip()
            if len(c) > 30:
                return c[:220].rsplit(" ", 1)[0] + ("…" if len(c) > 220 else "")
    return ""


def main(root: str) -> None:
    rootp = Path(root)
    cats = {}
    sc = rootp / "context" / "search_categories.json"
    if sc.exists():
        cats = {x["filename"]: x.get("category") or "" for x in json.loads(sc.read_text())}
    items, left = [], 0
    for f in sorted((rootp / "workflows").glob("**/*.json")):
        data = f.read_bytes()
        try:
            doc = N.parse(data.decode("utf-8"))
            sdoc, _found = L.scrub(doc)
            plan = N.convert(sdoc)
            D.validate_steps(plan["steps"])
        except Exception:   # noqa: BLE001 - not a workflow Hoola can bring in: left out of the library
            left += 1
            continue
        rep = plan["report"]
        n_conv, n_ph = len(rep["converted"]), len(rep["placeholders"])
        checks = [c for c in rep["check"] if "Sign-ins" not in c.get("why", "")]
        ready = "partial" if n_ph else ("check" if checks else "ready")
        types = [N._short(n.get("type")) for n in doc.get("nodes") or [] if isinstance(n, dict)]
        apps = []
        for t in types:
            b = re.sub(r"(Trigger|Tool)$", "", t)
            if t in CORE or b in CORE or N.SUB_NODE.match(t) and not t.startswith("lmChat"):
                continue
            nm = nice(t)
            if nm not in apps:
                apps.append(nm)
        name = str(doc.get("name") or f.stem.split("_", 1)[-1].replace("_", " ")).strip()[:120]
        items.append({"id": f.stem, "p": str(f.relative_to(rootp / "workflows")).replace("\\", "/"), "n": name,
                      "c": cats.get(f.name) or "Other", "a": apps[:8], "t": plan["trigger"],
                      "k": len([t for t in types if t != "stickyNote"]), "s": hashlib.sha256(data).hexdigest(),
                      "b": len(data), "r": ready, "cv": n_conv, "ph": n_ph,
                      "sh": round(n_conv / (n_conv + n_ph), 2) if (n_conv + n_ph) else 1.0, "d": describe(doc)})
    seen, uniq = set(), []
    for x in items:                       # the repo has the same file twice in some folders
        if x["s"] in seen:
            continue
        seen.add(x["s"])
        uniq.append(x)
    out = {"source": L.SOURCE, "items": uniq, "left_out": left}
    L.INDEX_FILE.write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode(), 9, mtime=0))
    r = {k: sum(1 for x in uniq if x["r"] == k) for k in ("ready", "check", "partial")}
    print(f"{len(uniq)} workflows ({r}), {left} left out, {L.INDEX_FILE.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1])
