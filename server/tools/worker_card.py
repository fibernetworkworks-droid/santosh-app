"""Worker card: every candidate worker model does Hoola's own worker jobs, measured (19 Nov 2026).

Why: the atlas (docs/research/claude_chat/08_worker_atlas.md) compared models on public boards and ONE list price each.
Two things it could not see: (1) on OpenRouter one model is served by up to 50 providers at prices up to 19x apart, and
the Box asks for the FASTEST one (provider.sort = latency), so the list price is not what Hoola pays; (2) a board rates
general answers, not Hoola's worker jobs (a sum in Hinglish, an order turned into JSON, the right tool, a plan count).

What it does: each model gets the same 11 jobs, each checked by code (never by another model), sent exactly the way the
Box sends a call (reasoning effort low and streamed, provider.sort from pipeline_provider_sort), 3 runs each for a
candidate, 1 run for the expensive reference models, plus one run per job routed to the CHEAPEST provider
(provider.sort = price) to show what the cheaper route costs and whether it still passes. Every call records the
provider that answered, the first-token time, the whole time, the tokens (incl. hidden reasoning) and the rupees
OpenRouter actually charged (usage.cost). A ceiling in rupees stops the card before it is passed.

Runs on the VPS from the app's folder (the server's own OpenRouter key, never printed):
    cd ~/apps/santosh-core && .venv/bin/python worker_card.py --budget-inr 400
    .venv/bin/python worker_card.py --status            # the newest saved card again
    .venv/bin/python worker_card.py --selftest          # the checkers on planted answers, no network, Rs 0
Saved: data/quality/worker-card-<time>.json.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import base64
import glob
import io
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time

INR = 88.0                       # rupees to the dollar, same as the atlas
URL = "https://openrouter.ai/api/v1/chat/completions"
REASONING_ROOM = 2048            # what the Box adds to max_tokens for the reasoning (glm_reasoning_room)

# (model, role, company). role: "cand" = 3 runs Box routing + 1 run cheapest routing; "ref" = 1 run (what the Box picked
# or would move up to - expensive, kept to one run so the card stays cheap).
MODELS = [
    ("deepseek/deepseek-v4.1-flash-1017", "cand", "DeepSeek"),
    ("z-ai/glm-5.3", "cand", "Z.AI"),
    ("z-ai/glm-5.3-flash", "cand", "Z.AI"),
    ("qwen/qwen3.8-27b", "cand", "Alibaba"),
    ("qwen/qwen3.8-flash", "cand", "Alibaba"),
    ("xiaomi/mimo-v2.6-pro", "cand", "Xiaomi"),
    ("xiaomi/mimo-v2.6-flash", "cand", "Xiaomi"),
    ("google/gemini-3.8-flash", "cand", "Google"),
    ("google/gemini-3.5-flash-lite", "cand", "Google"),
    ("tencent/hy4", "cand", "Tencent"),
    ("tencent/hy4-flash", "cand", "Tencent"),
    ("tencent/hy3", "cand", "Tencent"),
    ("openai/gpt-6.1-terra", "cand", "OpenAI"),
    ("openai/gpt-5.6-luna", "cand", "OpenAI"),
    ("moonshotai/kimi-k3.1-pro", "cand", "Moonshot"),
    ("meta/muse-spark-1.3", "cand", "Meta"),
    ("qwen/qwen3.8-max-0902", "cand", "Alibaba"),
    ("anthropic/claude-haiku-5.5", "cand", "Anthropic"),
    ("anthropic/claude-sonnet-4.6", "ref", "Anthropic"),
    ("anthropic/claude-opus-4.6", "ref", "Anthropic"),
    ("anthropic/claude-sonnet-5.5", "ref", "Anthropic"),
    ("anthropic/claude-opus-5.5", "ref", "Anthropic"),
]

TOOLS = [
    {"type": "function", "function": {"name": "web_search", "description": "Search the web for live information.",
                                      "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                                                     "required": ["query"]}}},
    {"type": "function", "function": {"name": "pylab", "description": "Run Python code to calculate.",
                                      "parameters": {"type": "object", "properties": {"code": {"type": "string"}},
                                                     "required": ["code"]}}},
    {"type": "function", "function": {"name": "create_reminder", "description": "Set a reminder for the user.",
                                      "parameters": {"type": "object", "properties": {"text": {"type": "string"},
                                                                                      "when": {"type": "string"}},
                                                     "required": ["text", "when"]}}},
    {"type": "function", "function": {"name": "email_draft", "description": "Draft an email for the user to approve.",
                                      "parameters": {"type": "object", "properties": {"to": {"type": "string"},
                                                                                      "subject": {"type": "string"},
                                                                                      "body": {"type": "string"}},
                                                     "required": ["to", "subject", "body"]}}},
]
TOOL_SYS = ("You are Hoola, a coworker for an Indian small-business owner. Use a tool only when the answer needs live "
            "information or an action. Explain things you know directly.")

INVOICE_LINES = ["TAX INVOICE", "Shree Ganesh Traders, Pune", "GSTIN: 27AAGCS1234F1Z5", "",
                 "Kaju W240     2 kg x 1,040  =  2,080", "Chai patti    3 x 240       =    720", "",
                 "Taxable value               2,800", "GST 5%                        140", "TOTAL          Rs 2,940"]

# kind = the Box worker kind the job stands for (W2's pipeline_workers lists)
TASKS = [
    {"id": "math_profit", "kind": "working out", "max": 900, "msgs": [
        {"role": "user", "content": "October ka hisaab: sales Rs 1,84,000, kachcha maal Rs 1,12,500, kiraya Rs 25,000, "
                                    "staff Rs 18,000. Profit kitna hua aur profit margin kitne % hai? Final answer do."}]},
    {"id": "math_gst", "kind": "working out", "max": 900, "msgs": [
        {"role": "user", "content": "Ek item ki keemat Rs 4,500 hai (GST alag se), GST 18%. Maharashtra ke andar hi "
                                    "bechna hai. CGST, SGST aur total bill kitna banega?"}]},
    {"id": "extract_json", "kind": "extraction / tables", "max": 700, "msgs": [
        {"role": "system", "content": "Reply with JSON only. No words before or after it."},
        {"role": "user", "content": "Turn this WhatsApp order into JSON with keys customer (string), phone (digits "
                                    "only), items (list of {name, qty, unit_price}) and total (number).\n\n"
                                    "\"Bhaiya Ramesh bol raha hu, 98220 11223. 2 kg kaju (Rs 1,100 per kg) aur 3 packet "
                                    "chai patti Rs 240 wali bhej dena, ek Amul butter 500g bhi - Rs 285. Kal subah tak "
                                    "chahiye.\""}]},
    {"id": "table_exact", "kind": "extraction / tables", "max": 600, "msgs": [
        {"role": "user", "content": "Make a markdown table with exactly three columns: Product, Price (Rs), Stock. "
                                    "Rows: Kaju, 1100 per kg, 12 kg; Chai patti, 240 per packet, 40 packets; Amul "
                                    "butter, 285 per pack, 9 packs. Reply with the table only - no line before or "
                                    "after it."}]},
    {"id": "facts_note", "kind": "facts from her papers", "max": 600, "msgs": [
        {"role": "system", "content": "Answer ONLY from the supplier note below. If something is not in the note, say "
                                      "plainly that it is not in the note.\n\nSUPPLIER NOTE: Shree Ganesh Traders, "
                                      "Pune. Kaju W240 Rs 1,040 per kg, minimum order 10 kg. Delivery to Akola in 4 "
                                      "days by Patil Transport. Payment 50% advance, rest on delivery. Contact: "
                                      "Mahesh Joshi, 98500 44120."},
        {"role": "user", "content": "Kaju ka rate kya hai, Akola delivery kitne din mein hogi, aur inka GST number "
                                    "kya hai?"}]},
    {"id": "tool_needed", "kind": "tool choice", "max": 500, "tools": True, "msgs": [
        {"role": "system", "content": TOOL_SYS},
        {"role": "user", "content": "Aaj Mumbai mein 24 carat sone ka rate kya chal raha hai?"}]},
    {"id": "tool_not_needed", "kind": "tool choice", "max": 600, "tools": True, "msgs": [
        {"role": "system", "content": TOOL_SYS},
        {"role": "user", "content": "GST composition scheme kya hota hai? 3 line mein samjhao."}]},
    {"id": "planner_parts", "kind": "planner", "max": 400, "msgs": [
        {"role": "system", "content": "You plan work for an assistant. A message needs several worker parts ONLY when "
                                      "it asks for 2-5 independent things to look up or compare, or several files to "
                                      "read. Anything one writer can answer in one reply is 1 part, even with 'and', "
                                      "commas or a list. Reply JSON only: {\"A\": n, \"B\": n, \"C\": n, \"D\": n} = "
                                      "the number of parts for each message."},
        {"role": "user", "content": "A: 4 Diwali offer ideas do aur ek discount bhi suggest karo\n"
                                    "B: Aaj gold, silver aur petrol ke rate compare karke batao\n"
                                    "C: Sales Rs 1,84,000, costs Rs 1,12,500, aur rent Rs 25,000 hai - profit batao\n"
                                    "D: Is email ka reply likho aur usse thoda chhota bhi karo"}]},
    {"id": "hindi_reply", "kind": "Indian languages", "max": 700, "msgs": [
        {"role": "user", "content": "UPI QR कोड से दुकान पर पेमेंट कैसे लेते हैं? 3 आसान स्टेप में बताइए।"}]},
    {"id": "read_picture", "kind": "reading pictures", "max": 400, "image": True, "msgs": [
        {"role": "user", "content": "Is bill ka total amount aur GSTIN batao."}]},
    {"id": "code_fn", "kind": "code", "max": 1200, "msgs": [
        {"role": "user", "content": "Write a Python function inr_to_int(s: str) -> int that turns Indian money text "
                                    "into whole rupees. It must handle: 'Rs 1,84,000' -> 184000, '₹25,000.50' -> "
                                    "25000, 'INR 4,500/-' -> 4500, '1.2 lakh' -> 120000, '3 crore' -> 30000000, "
                                    "'Rs. 999' -> 999. Standard library only. Reply with only the code in one "
                                    "```python block."}]},
]

CODE_TESTS = [("Rs 1,84,000", 184000), ("₹25,000.50", 25000), ("INR 4,500/-", 4500), ("1.2 lakh", 120000),
              ("3 crore", 30000000), ("Rs. 999", 999)]


# ---------------------------------------------------------------- checks (code only, never a model)

def _num(text: str) -> str:
    return re.sub(r"(?<=\d),(?=\d)", "", text or "")


def _has(text: str, n) -> bool:
    return re.search(r"(?<![\d.])" + re.escape(str(n)) + r"(?![\d])", _num(text)) is not None


def _json_of(text: str):
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t.strip(), flags=re.S)
    try:
        return json.loads(t)
    except Exception:   # noqa: BLE001
        m = re.search(r"\{.*\}", t, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:   # noqa: BLE001
                return None
    return None


_BANNED = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr",
           "delattr", "input", "breakpoint", "help", "exit", "quit", "memoryview"}


def _code_safe(code: str) -> str:
    """'' when the code may run (pure function, re / math / decimal only), else why not."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"does not parse ({e.msg})"
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
            if any(m.split(".")[0] not in ("re", "math", "decimal", "typing", "fractions") for m in mods):
                return "imports " + ",".join(mods)
        if isinstance(n, ast.Name) and n.id in _BANNED:
            return "uses " + n.id
        if isinstance(n, ast.Attribute) and n.attr.startswith("__"):
            return "uses " + n.attr
    if not any(isinstance(n, ast.FunctionDef) and n.name == "inr_to_int" for n in tree.body):
        return "no inr_to_int function"
    return ""


def _run_code(code: str) -> tuple[bool, str]:
    why = _code_safe(code)
    if why:
        return False, "code not run: " + why
    prog = code + "\n\nimport json as _j\n_r = []\nfor _s, _w in " + repr(CODE_TESTS) + ":\n" \
        "    try:\n        _g = inr_to_int(_s)\n    except Exception as _e:\n        _g = 'error ' + type(_e).__name__\n" \
        "    _r.append([_s, _w, _g])\nprint(_j.dumps(_r, default=str))\n"

    def _limits():
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
            resource.setrlimit(resource.RLIMIT_AS, (256 << 20, 256 << 20))
            resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
        except Exception:   # noqa: BLE001
            pass

    with tempfile.TemporaryDirectory() as d:
        try:
            p = subprocess.run([sys.executable, "-I", "-S", "-c", prog], capture_output=True, text=True, timeout=6,
                               cwd=d, env={}, preexec_fn=_limits if os.name == "posix" else None)
        except subprocess.TimeoutExpired:
            return False, "code ran too long"
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:   # noqa: BLE001
        return False, "code crashed: " + (p.stderr or "").strip()[-120:]
    bad = [f"{s!r} -> {g!r} (want {w})" for s, w, g in res if g != w]
    return (not bad), ("all 6 cases right" if not bad else "wrong: " + "; ".join(bad[:3]))


def check(task_id: str, text: str, tool_calls: list) -> tuple[bool, str]:
    """(passed, why) for one answer, by code."""
    t = text or ""
    if task_id == "math_profit":
        ok_p, ok_m = _has(t, 28500), re.search(r"15\.4[89]|15\.5(?!\d)", t) is not None
        return ok_p and ok_m, ("profit 28,500 and margin 15.49%" if ok_p and ok_m else
                               f"profit 28,500 {'found' if ok_p else 'MISSING'}, margin 15.49% {'found' if ok_m else 'MISSING'}")
    if task_id == "math_gst":
        ok = _has(t, 405) and _has(t, 5310)
        return ok, "CGST 405 + SGST 405 + total 5,310" if ok else "405 / 5,310 missing"
    if task_id == "extract_json":
        j = _json_of(t)
        if not isinstance(j, dict):
            return False, "not JSON"
        items = j.get("items") or []
        try:
            got = sorted((float(i.get("qty")), float(i.get("unit_price"))) for i in items)
        except Exception:   # noqa: BLE001
            return False, "items not numbers"
        want = [(1.0, 285.0), (2.0, 1100.0), (3.0, 240.0)]
        phone = re.sub(r"\D", "", str(j.get("phone", "")))
        try:
            total = float(j.get("total"))
        except Exception:   # noqa: BLE001
            total = -1
        errs = []
        if "ramesh" not in str(j.get("customer", "")).lower():
            errs.append("customer")
        if phone[-10:] != "9822011223":
            errs.append("phone")
        if got != want:
            errs.append("items")
        if abs(total - 3205) > 0.01:
            errs.append(f"total {j.get('total')}")
        return not errs, "exact" if not errs else "wrong " + ", ".join(errs)
    if task_id == "table_exact":
        lines = [ln.strip() for ln in t.strip().splitlines() if ln.strip()]
        lines = [ln for ln in lines if not ln.startswith("```")]
        ok = (len(lines) == 5 and all(ln.startswith("|") for ln in lines)
              and all(w in lines[0].lower() for w in ("product", "price", "stock"))
              and re.match(r"^\|[\s:\-|]+\|?$", lines[1]) is not None)
        return ok, "table only, 3 rows" if ok else f"{len(lines)} lines / extra words or wrong header"
    if task_id == "facts_note":
        rate, days = _has(t, 1040), re.search(r"\b4\s*(din|days?|दिन)", t, re.I) is not None
        said = re.search(r"not (in|mentioned|given|provided|available|listed|included)|isn'?t (in|mentioned|given)|"
                         r"doesn'?t (say|mention|include|have)|no (gst|mention)|nahi|nahin|नहीं|उपलब्ध नहीं", t, re.I)
        invented = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b", t)
        ok = rate and days and said is not None and not invented
        return ok, "1,040 + 4 days + 'GST not in the note'" if ok else (
            "INVENTED a GSTIN" if invented else
            f"rate {'ok' if rate else 'MISSING'}, days {'ok' if days else 'MISSING'}, not-in-note {'said' if said else 'NOT SAID'}")
    if task_id == "tool_needed":
        if not tool_calls:
            return False, "answered without searching (no tool)"
        n = tool_calls[0].get("name")
        try:
            q = str(json.loads(tool_calls[0].get("arguments") or "{}").get("query", ""))
        except Exception:   # noqa: BLE001
            q = ""
        ok = n == "web_search" and re.search(r"gold|sona|sone|सोन|24", q, re.I) is not None
        return ok, f"web_search '{q[:40]}'" if ok else f"called {n} '{q[:40]}'"
    if task_id == "tool_not_needed":
        if tool_calls:
            return False, "ran a tool on a plain question: " + ",".join(c.get("name") or "?" for c in tool_calls)
        ok = "composition" in t.lower() and len(t) < 1500
        return ok, "answered directly" if ok else ("too long" if len(t) >= 1500 else "no explanation")
    if task_id == "planner_parts":
        j = _json_of(t)
        want = {"A": 1, "B": 3, "C": 1, "D": 1}
        if not isinstance(j, dict):
            return False, "not JSON"
        got = {k: j.get(k) for k in want}
        ok = all(str(got[k]) == str(v) for k, v in want.items())
        return ok, "A1 B3 C1 D1" if ok else "got " + json.dumps(got)
    if task_id == "hindi_reply":
        letters = re.findall(r"[A-Za-z\u0900-\u097F]", t)
        dev = sum(1 for c in letters if "\u0900" <= c <= "\u097F")
        share = dev / len(letters) if letters else 0
        steps = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)]|[१२३४५][.)]|\*\*\d)", t))
        ok = share >= 0.6 and steps >= 3
        return ok, f"Hindi {share:.0%}, {steps} steps" + ("" if ok else " (need Hindi >= 60% and 3 steps)")
    if task_id == "read_picture":
        ok_t = _has(t, 2940)
        ok_g = "27AAGCS1234F1Z5" in re.sub(r"\s", "", t).upper()
        return ok_t and ok_g, ("total 2,940 + GSTIN" if ok_t and ok_g else
                               f"total {'ok' if ok_t else 'WRONG'}, GSTIN {'ok' if ok_g else 'WRONG'}")
    if task_id == "code_fn":
        m = re.search(r"```(?:python)?\s*\n(.*?)```", t, re.S)
        return _run_code(m.group(1) if m else t)
    return False, "unknown job"


# ---------------------------------------------------------------- the picture (made here, same every time)

def invoice_png() -> str:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (980, 560), "white")
    d = ImageDraw.Draw(img)
    font = None
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            font = ImageFont.truetype(f, 30)
            break
    if font is None:
        try:
            font = ImageFont.load_default(size=30)
        except TypeError:
            font = ImageFont.load_default()
    y = 30
    for ln in INVOICE_LINES:
        d.text((40, y), ln, fill="black", font=font)
        y += 50
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- one call, the way the Box sends it

class Stop(Exception):
    pass


async def call(client, key: str, model: str, task: dict, sort: str, image: str) -> dict:
    msgs = json.loads(json.dumps(task["msgs"]))
    if task.get("image"):
        msgs[-1]["content"] = [{"type": "text", "text": msgs[-1]["content"]},
                               {"type": "image_url", "image_url": {"url": image}}]
    body = {"model": model, "messages": msgs, "stream": True, "max_tokens": task["max"] + REASONING_ROOM,
            "reasoning": {"effort": "low", "exclude": False}, "usage": {"include": True}}
    if sort:
        body["provider"] = {"sort": sort}
    if task.get("tools"):
        body["tools"] = TOOLS
    head = {"Authorization": f"Bearer {key}", "X-Title": "Hoola worker card"}
    t0 = time.monotonic()
    out = {"text": "", "tools": {}, "first_any": None, "first_word": None, "provider": "", "usage": {}, "error": ""}
    for attempt in (1, 2):
        try:
            async with client.stream("POST", URL, json=body, headers=head, timeout=150) as r:
                if r.status_code != 200:
                    txt = (await r.aread()).decode("utf-8", "replace")
                    if r.status_code in (400, 422) and "reasoning" in txt.lower() and attempt == 1:
                        body.pop("reasoning", None)
                        continue
                    if r.status_code in (402, 403) and ("limit" in txt.lower() or "credit" in txt.lower()):
                        raise Stop(f"OpenRouter {r.status_code}: {txt[:200]}")
                    out["error"] = f"HTTP {r.status_code}: {txt[:160]}"
                    break
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        ch = json.loads(data)
                    except Exception:   # noqa: BLE001
                        continue
                    if ch.get("error"):
                        out["error"] = "stream: " + str(ch["error"].get("message", ch["error"]))[:160]
                    out["provider"] = ch.get("provider") or out["provider"]
                    if ch.get("usage"):
                        out["usage"] = ch["usage"]
                    for c in ch.get("choices") or []:
                        dl = c.get("delta") or {}
                        now = time.monotonic() - t0
                        if (dl.get("reasoning") or dl.get("content") or dl.get("tool_calls")) and out["first_any"] is None:
                            out["first_any"] = now
                        if dl.get("content"):
                            out["text"] += dl["content"]
                            if out["first_word"] is None:
                                out["first_word"] = now
                        for tc in dl.get("tool_calls") or []:
                            slot = out["tools"].setdefault(tc.get("index", 0), {"name": "", "arguments": ""})
                            fn = tc.get("function") or {}
                            slot["name"] = fn.get("name") or slot["name"]
                            slot["arguments"] += fn.get("arguments") or ""
                            if out["first_word"] is None:
                                out["first_word"] = now
            break
        except Stop:
            raise
        except Exception as e:   # noqa: BLE001
            out["error"] = f"{type(e).__name__}: {str(e)[:120]}"
            break
    out["secs"] = round(time.monotonic() - t0, 2)
    out["tools"] = [out["tools"][k] for k in sorted(out["tools"])]
    return out


# ---------------------------------------------------------------- the card

def _key() -> str:
    sys.path.insert(0, os.getcwd())
    from app.agent.providers import key_of   # the running app's own key lookup (VPS .env)
    k = key_of("openrouter")
    if not k:
        raise SystemExit("no OpenRouter key on this server")
    return k


def _box_sort() -> str:
    try:
        from app.config import get_settings
        return str(get_settings().pipeline_provider_sort or "")
    except Exception:   # noqa: BLE001
        return "latency"


async def run_card(budget_inr: float, deadline_s: float, only: list[str]) -> dict:
    import httpx
    key = _key()
    box_sort = _box_sort()
    models = [m for m in MODELS if not only or m[0] in only]
    async with httpx.AsyncClient() as client:
        r = await client.get("https://openrouter.ai/api/v1/models", timeout=30)
        listed = {m["id"]: m for m in r.json().get("data", [])}
    vision = {mid for mid, m in listed.items() if "image" in (m.get("architecture") or {}).get("input_modalities", [])}
    missing = [m[0] for m in models if m[0] not in listed]
    models = [m for m in models if m[0] in listed]
    image = invoice_png()
    jobs = []      # (run, routing, model, task) in an order that keeps coverage even if the ceiling stops the card
    for run in range(3):
        for t in TASKS:
            for mid, role, _co in models:
                if t.get("image") and mid not in vision:
                    continue
                if role == "ref" and run > 0:
                    continue
                jobs.append((run, "box", mid, t))
    for t in TASKS:
        for mid, role, _co in models:
            if role == "cand" and not (t.get("image") and mid not in vision):
                jobs.append((9, "cheapest", mid, t))
    spent = {"usd": 0.0}
    rows, stopped = [], {"why": ""}
    sem = asyncio.Semaphore(12)
    t_start = time.monotonic()
    print(f"== worker card: {len(models)} models x {len(TASKS)} jobs = {len(jobs)} calls, Box routing provider.sort="
          f"'{box_sort}', ceiling Rs {budget_inr:.0f}" + (f" | not on OpenRouter now: {', '.join(missing)}" if missing else ""),
          flush=True)

    async def one(job):
        run, routing, mid, t = job
        async with sem:
            if stopped["why"]:
                return
            if spent["usd"] * INR >= budget_inr:
                stopped["why"] = f"rupee ceiling reached (Rs {spent['usd'] * INR:.0f})"
                return
            if time.monotonic() - t_start > deadline_s:
                stopped["why"] = f"time limit {deadline_s / 60:.0f} min reached"
                return
            try:
                async with httpx.AsyncClient() as client:
                    res = await call(client, key, mid, t, box_sort if routing == "box" else "price", image)
            except Stop as e:
                stopped["why"] = str(e)
                return
            u = res.get("usage") or {}
            cost = float(u.get("cost") or 0.0)
            spent["usd"] += cost
            ok, why = (False, res["error"]) if res["error"] and not (res["text"] or res["tools"]) else \
                check(t["id"], res["text"], res["tools"])
            ctd = u.get("completion_tokens_details") or {}
            rows.append({"model": mid, "task": t["id"], "kind": t["kind"], "run": run, "routing": routing,
                         "ok": ok, "why": why, "provider": res["provider"], "secs": res["secs"],
                         "first_any": res["first_any"], "first_word": res["first_word"], "inr": round(cost * INR, 4),
                         "in_tok": u.get("prompt_tokens"), "out_tok": u.get("completion_tokens"),
                         "reason_tok": ctd.get("reasoning_tokens"), "error": res["error"],
                         "answer": (res["text"] or json.dumps(res["tools"]))[:300]})
            if len(rows) % 50 == 0:
                print(f"   {len(rows)}/{len(jobs)} calls, Rs {spent['usd'] * INR:.1f} so far", flush=True)

    await asyncio.gather(*(one(j) for j in jobs))
    return {"at": int(time.time()), "box_sort": box_sort, "budget_inr": budget_inr, "spent_inr": round(spent["usd"] * INR, 2),
            "calls_planned": len(jobs), "calls_done": len(rows), "stopped": stopped["why"], "missing": missing,
            "models": [list(m) for m in models], "rows": rows,
            "list_price": {mid: {"in": float(listed[mid]["pricing"]["prompt"]) * 1e6,
                                 "out": float(listed[mid]["pricing"]["completion"]) * 1e6} for mid, _r, _c in models}}


# ---------------------------------------------------------------- the report

def _med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def _f(x, nd=1, pre=""):
    return "-" if x is None else f"{pre}{x:.{nd}f}"


def report(card: dict) -> str:
    rows, out = card["rows"], []
    company = {m[0]: m[2] for m in card["models"]}
    role = {m[0]: m[1] for m in card["models"]}
    out.append(f"WORKER CARD {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(card['at']))} | Box routing "
               f"provider.sort='{card['box_sort']}' | {card['calls_done']}/{card['calls_planned']} calls | spent Rs "
               f"{card['spent_inr']}" + (f" | STOPPED: {card['stopped']}" if card.get("stopped") else ""))
    out.append("Each job checked by code. 'all 3' = the job passed in every Box-routed run (pass^3). Rs = what "
               "OpenRouter charged, per job, median. s = whole answer, median; 1st = first token (thinking counts).")
    box = [r for r in rows if r["routing"] == "box"]
    by_model: dict[str, list] = {}
    for r in box:
        by_model.setdefault(r["model"], []).append(r)
    summary = []
    for mid, rs in by_model.items():
        tasks = sorted({r["task"] for r in rs})
        allk = [t for t in tasks if all(r["ok"] for r in rs if r["task"] == t)]
        provs: dict[str, int] = {}
        for r in rs:
            provs[r["provider"] or "?"] = provs.get(r["provider"] or "?", 0) + 1
        ch = [r for r in rows if r["model"] == mid and r["routing"] == "cheapest"]
        summary.append({"model": mid, "co": company.get(mid, ""), "role": role.get(mid, ""),
                        "pass": sum(r["ok"] for r in rs), "n": len(rs), "all3": len(allk), "tasks": len(tasks),
                        "inr": _med([r["inr"] for r in rs]), "secs": _med([r["secs"] for r in rs]),
                        "first": _med([r["first_any"] for r in rs]), "reason": _med([r["reason_tok"] for r in rs]),
                        "errors": sum(1 for r in rs if r["error"]),
                        "provs": ", ".join(f"{p} {n}" for p, n in sorted(provs.items(), key=lambda x: -x[1])[:3]),
                        "ch_pass": sum(r["ok"] for r in ch), "ch_n": len(ch), "ch_inr": _med([r["inr"] for r in ch]),
                        "ch_prov": ", ".join(sorted({r["provider"] for r in ch if r["provider"]}))[:40],
                        "fails": sorted({f"{r['task']}: {r['why']}" for r in rs if not r["ok"]})})
    summary.sort(key=lambda s: (-(s["all3"] / max(1, s["tasks"])), s["inr"] if s["inr"] is not None else 99))
    out.append("")
    out.append(f"{'model':36} {'pass':>7} {'all3':>6} {'Rs/job':>7} {'s':>5} {'1st':>5} {'think':>6} {'err':>3} | "
               f"{'cheapest route: pass Rs/job':>28} | served by (Box route)")
    for s in summary:
        out.append(f"{s['model'][:36]:36} {s['pass']:>3}/{s['n']:<3} {s['all3']:>2}/{s['tasks']:<3} "
                   f"{_f(s['inr'], 3):>7} {_f(s['secs']):>5} {_f(s['first']):>5} {_f(s['reason'], 0):>6} "
                   f"{s['errors']:>3} | {s['ch_pass']:>3}/{s['ch_n']:<3} {_f(s['ch_inr'], 3):>7} {s['ch_prov'][:16]:16} | "
                   f"{s['provs']}" + ("  [reference, 1 run]" if s["role"] == "ref" else ""))
    # picks by rule, per worker kind: passed every run of every job of the kind, then cheapest; backup = another company
    out.append("")
    out.append("PICKS BY RULE (passed every Box-routed run of every job of the kind -> cheapest median Rs/job; backup = "
               "next cheapest from another company; ties within 10% -> faster):")
    kinds: dict[str, list] = {}
    for t in TASKS:
        kinds.setdefault(t["kind"], []).append(t["id"])
    for kind, tids in kinds.items():
        good = []
        for mid, rs in by_model.items():
            rk = [r for r in rs if r["task"] in tids]
            if not rk or {r["task"] for r in rk} != set(tids) or not all(r["ok"] for r in rk):
                continue
            if any(sum(1 for r in rk if r["task"] == t) < (1 if role.get(mid) == "ref" else 3) for t in tids):
                continue
            good.append((_med([r["inr"] for r in rk]) or 0, _med([r["secs"] for r in rk]) or 0, mid))
        good.sort()
        if good:
            # within 10% of the cheapest -> the faster one wins
            cheap = good[0][0]
            close = sorted([g for g in good if g[0] <= cheap * 1.1 + 0.001], key=lambda g: g[1])
            main = close[0]
            back = next((g for g in good if company.get(g[2]) != company.get(main[2])), None)
            out.append(f"  {kind:24} main {main[2]} (Rs {main[0]:.3f}/job, {main[1]:.1f} s)" +
                       (f" | backup {back[2]} (Rs {back[0]:.3f}, {back[1]:.1f} s)" if back else " | no backup passed") +
                       f" | {len(good)} models passed every run")
        else:
            out.append(f"  {kind:24} NO model passed every run - see the failures below")
    out.append("")
    out.append("WHAT WENT WRONG (Box route, each different reason once):")
    for s in summary:
        if s["fails"]:
            out.append(f"  {s['model']}: " + " | ".join(s["fails"][:6]))
    return "\n".join(out)


def _save(card: dict) -> str:
    os.makedirs("data/quality", exist_ok=True)
    p = f"data/quality/worker-card-{time.strftime('%Y%m%d-%H%M%S')}.json"
    with open(p, "w") as f:
        json.dump(card, f, ensure_ascii=False, indent=1)
    return p


def selftest() -> int:
    """The checkers on planted right and wrong answers - every right one passes, every wrong one fails."""
    cases = [
        ("math_profit", "Profit = Rs 28,500. Margin = 15.49%", [], True),
        ("math_profit", "Profit = Rs 46,500. Margin = 25.3%", [], False),
        ("math_gst", "CGST 9% = Rs 405, SGST 9% = Rs 405, total Rs 5,310", [], True),
        ("math_gst", "GST Rs 810, total Rs 5,210", [], False),
        ("extract_json", '{"customer":"Ramesh","phone":"9822011223","items":[{"name":"kaju","qty":2,"unit_price":1100},'
                         '{"name":"chai patti","qty":3,"unit_price":240},{"name":"Amul butter","qty":1,"unit_price":285}],'
                         '"total":3205}', [], True),
        ("extract_json", '{"customer":"Ramesh","phone":"9822011223","items":[],"total":3205}', [], False),
        ("table_exact", "| Product | Price (Rs) | Stock |\n|---|---|---|\n| Kaju | 1100 per kg | 12 kg |\n| Chai patti | 240 "
                        "| 40 |\n| Amul butter | 285 | 9 |", [], True),
        ("table_exact", "Here is your table:\n| Product | Price (Rs) | Stock |\n|---|---|---|\n| Kaju | 1100 | 12 |", [], False),
        ("facts_note", "Kaju Rs 1,040 per kg. Akola delivery 4 days. GST number is not in the note.", [], True),
        ("facts_note", "Kaju Rs 1,040 per kg, 4 days, GSTIN 27AAGCS1234F1Z5", [], False),
        ("tool_needed", "", [{"name": "web_search", "arguments": '{"query": "gold rate Mumbai today 24 carat"}'}], True),
        ("tool_needed", "Aaj gold ka rate Rs 7,500 hai", [], False),
        ("tool_not_needed", "Composition scheme chhote business ke liye hai: kam rate par GST.", [], True),
        ("tool_not_needed", "", [{"name": "web_search", "arguments": '{"query": "composition"}'}], False),
        ("planner_parts", '{"A": 1, "B": 3, "C": 1, "D": 1}', [], True),
        ("planner_parts", '{"A": 2, "B": 3, "C": 3, "D": 2}', [], False),
        ("hindi_reply", "1. ग्राहक को QR कोड दिखाइए\n2. वह अपने UPI ऐप से स्कैन करे\n3. पैसा आने का मैसेज देखिए", [], True),
        ("hindi_reply", "1. Show the QR code\n2. Customer scans\n3. Check the message", [], False),
        ("read_picture", "Total Rs 2,940, GSTIN 27AAGCS1234F1Z5", [], True),
        ("read_picture", "Total Rs 2,800", [], False),
        ("code_fn", "```python\nimport re\ndef inr_to_int(s: str) -> int:\n    t = s.lower().replace(',', '')\n"
                    "    m = re.search(r'(\\d+(?:\\.\\d+)?)', t)\n    v = float(m.group(1))\n    if 'crore' in t: v *= 1e7\n"
                    "    elif 'lakh' in t: v *= 1e5\n    return int(v + 1e-9)\n```", [], True),
        ("code_fn", "```python\nimport os\ndef inr_to_int(s): return os.system('ls')\n```", [], False),
        ("code_fn", "```python\ndef inr_to_int(s): return 0\n```", [], False),
    ]
    bad = 0
    for tid, text, tools, want in cases:
        ok, why = check(tid, text, tools)
        if ok != want:
            bad += 1
            print(f"SELFTEST WRONG {tid}: want {want}, got {ok} ({why})")
    try:
        invoice_png()
        pic = "picture made"
    except Exception as e:   # noqa: BLE001
        pic = f"picture NOT made ({e})"
        bad += 1
    print(f"selftest: {len(cases) - bad if bad <= len(cases) else 0}/{len(cases)} checker cases right, {pic}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-inr", type=float, default=400.0)
    ap.add_argument("--minutes", type=float, default=38.0)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated model ids")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.status:
        fs = sorted(glob.glob("data/quality/worker-card-*.json"))
        if not fs:
            print("no worker card saved yet - run worker_card")
            return 0
        print(report(json.load(open(fs[-1]))))
        print("\nsaved:", os.path.basename(fs[-1]))
        return 0
    if selftest():
        print("checkers are wrong - nothing spent")
        return 1
    card = asyncio.run(run_card(a.budget_inr, a.minutes * 60, [x for x in a.only.split(",") if x]))
    p = _save(card)
    print(report(card))
    print("\nsaved:", os.path.basename(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
