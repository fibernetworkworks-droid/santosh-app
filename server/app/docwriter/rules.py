"""Docs Sahayak rules: document types (Diataxis), languages, the safe step language for screenshots, the style guide
(plain language + Google developer style basics + her glossary), privacy masks, and the research sources.

Nothing here talks to the network or a model; it is plain code so tests and the app can rely on it."""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------- what Hoola never does
NEVER = (
    "Docs go public (Hoola page, GitHub, WordPress) only with your tap: the tool only sends a card.",
    "Never writes into docs what is not in the product: a price, number or date it does not know stays [blank].",
    "No screenshots of someone else's website / app: only your product (made in Hoola, or one you proved you own).",
    "Never fills a password / OTP / card / PIN in a screenshot; a customer's name / phone / email that shows is fully covered (not blurred).",
    "Never runs the code in your GitHub repo, only reads it (README, docs, OpenAPI, releases, merged PRs).",
    "No JavaScript in the step language: only goto / click / fill / select / press / wait / scroll / hover / screenshot.",
)

# ---------------------------------------------------------------- document types, mapped to Diataxis (Daniele Procida)
KINDS: dict[str, dict[str, Any]] = {
    "quickstart": {"label": "Quick start", "hi": "shuruaat (pehli baar)", "diataxis": "tutorial",
                   "goal": "A new user finishes one task for the first time: small steps, the result of each step, no options."},
    "howto": {"label": "How-to guide", "hi": "kaise karein", "diataxis": "how-to",
              "goal": "One task, one article: straight steps for a user who already knows the product; start with when it is useful."},
    "manual": {"label": "User manual", "hi": "user manual", "diataxis": "reference",
               "goal": "Every screen / page: what it is, what it shows, what you can do. Direct, complete, consistent."},
    "faq": {"label": "FAQ", "hi": "aksar poochhe sawaal", "diataxis": "explanation",
            "goal": "Real questions and short, clear answers; each answer links to the right page."},
    "admin": {"label": "Admin guide", "hi": "admin guide", "diataxis": "how-to",
              "goal": "Roles, permissions, ways to log in, approval chain, data and backup: the admin's work."},
    "api": {"label": "API reference", "hi": "API reference", "diataxis": "reference",
            "goal": "Every endpoint: method, path, what it does, parameters, body, response, errors, auth. From OpenAPI, from code."},
    "release_notes": {"label": "Release notes", "hi": "naya kya hai", "diataxis": "reference",
                      "goal": "What is new in this release, improvements, problems fixed, changes the user must make (breaking)."},
    "changelog": {"label": "Changelog", "hi": "badlav ki list", "diataxis": "reference",
                  "goal": "The date and changes of every version, newest on top."},
}
KIND_WORDS = (
    (r"quick\s*start|getting started|shuru|pehli baar|शुरु|सुरुवात", "quickstart"),
    (r"how\s*to|kaise|कैसे|कसे", "howto"),
    (r"faq|sawaal|सवाल|प्रश्न", "faq"),
    (r"admin|role|permission|adhikar", "admin"),
    (r"api|openapi|swagger|endpoint", "api"),
    (r"release\s*notes?|naya kya|kya naya|नया क्या", "release_notes"),
    (r"changelog|change\s*log|badlav ki list", "changelog"),
    (r"manual|guide|madad|help|मैनुअल|पुस्तिका", "manual"),
)


def guess_kind(text: str) -> str:
    t = (text or "").lower()
    for rx, k in KIND_WORDS:
        if re.search(rx, t, re.I):
            return k
    return "manual"


LANGS = {"en": "English", "hi": "Hindi (Devanagari)", "mr": "Marathi (Devanagari)", "hinglish": "Hinglish (Hindi in Latin letters, "
         "everyday English words kept)"}
LANG_WORDS = {"english": "en", "angrezi": "en", "hindi": "hi", "हिंदी": "hi", "हिन्दी": "hi", "marathi": "mr", "मराठी": "mr",
              "hinglish": "hinglish", "en": "en", "hi": "hi", "mr": "mr"}
HTML_LANG = {"en": "en", "hi": "hi", "mr": "mr", "hinglish": "hi-Latn"}


def lang_of(v: Any, default: str = "en") -> str:
    return LANG_WORDS.get(str(v or "").strip().lower(), default)


# ---------------------------------------------------------------- safe step language (no JavaScript, ever)
STEP_DO = ("goto", "click", "fill", "select", "press", "wait", "scroll", "hover", "screenshot")
KEYS = ("Enter", "Tab", "Escape", "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "PageDown", "PageUp", "Home", "End", "Space")
TARGET_KEYS = ("text", "label", "role", "name", "placeholder", "testid", "css", "alt", "title")
ROLES = ("button", "link", "textbox", "checkbox", "radio", "combobox", "tab", "menuitem", "heading", "switch", "option", "listitem",
         "img", "navigation", "dialog", "searchbox", "spinbutton")
SAFE_CSS = re.compile(r"^[A-Za-z0-9 #.\-_:>+~\[\]=\"'*,()]{1,120}$")
BAD_CSS = re.compile(r"(javascript|expression\(|url\(|\\|@import|<|>>)", re.I)
MAX_STEPS, MAX_SHOTS = 40, 20
SECRET_BOX = re.compile(r"(pass(word|code)?|pwd|otp|one[-_ ]?time|\bpin\b|mpin|cvv|cvc|card[-_ ]?(no|num)|cc-|upi[-_ ]?pin|secret|"
                        r"token|security[-_ ]?code)", re.I)
VIEWPORTS = {"phone": (390, 844, 2, True), "tablet": (820, 1180, 1, True), "desktop": (1366, 860, 1, False)}


class StepError(ValueError):
    pass


def secret_value(v: str) -> str:
    """Why a value to type looks like a secret (empty = fine). Demo values only: no OTP / card / PIN / Aadhaar / passwords."""
    s = str(v or "")
    digits = re.sub(r"\D", "", s)
    if re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b", s) or 13 <= len(digits) <= 19 and digits == re.sub(r"[\s-]", "", s):
        return "looks like a card number"
    if re.fullmatch(r"\d{4,8}", s.strip()):
        return "looks like an OTP / PIN"
    if re.fullmatch(r"\d{4}\s?\d{4}\s?\d{4}", s.strip()):
        return "looks like an Aadhaar number"
    if re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", s.strip().upper()) and s.strip().isupper():
        return "looks like a PAN"
    try:
        from ..net.policy import secret_found
        if secret_found(s):
            return "looks like a secret / key"
    except Exception:
        pass
    return ""


def clean_target(t: Any) -> dict[str, str]:
    if isinstance(t, str):
        t = {"text": t}
    if not isinstance(t, dict):
        raise StepError("bad target: {text|label|role+name|placeholder|testid|css}")
    out = {k: str(t[k]).strip()[:120] for k in TARGET_KEYS if t.get(k) not in (None, "")}
    if not out:
        raise StepError("the target is empty")
    if "role" in out and out["role"] not in ROLES:
        raise StepError(f"role '{out['role']}' is not allowed")
    if "css" in out and (not SAFE_CSS.match(out["css"]) or BAD_CSS.search(out["css"])):
        raise StepError("the css selector must be simple (id / class / attribute)")
    return out


def validate_steps(steps: Any, base_host: str = "") -> list[dict[str, Any]]:
    """Checks the steps BEFORE a browser opens. goto stays on her verified site; fill never takes a secret."""
    if not isinstance(steps, list) or not steps:
        raise StepError("a list of steps is needed")
    if len(steps) > MAX_STEPS:
        raise StepError(f"no more than {MAX_STEPS} steps in one flow")
    out, shots = [], 0
    for i, raw in enumerate(steps, 1):
        if isinstance(raw, str):
            raw = parse_step_line(raw)
        if not isinstance(raw, dict):
            raise StepError(f"step {i} not understood")
        do = str(raw.get("do") or raw.get("action") or "").strip().lower()
        if do not in STEP_DO:
            raise StepError(f"step {i}: '{do}' is not allowed (only {', '.join(STEP_DO)})")
        st: dict[str, Any] = {"do": do, "note": str(raw.get("note") or raw.get("say") or "").strip()[:200]}
        if do == "goto":
            url = str(raw.get("url") or raw.get("value") or "").strip()
            if not url:
                raise StepError(f"step {i}: goto needs a url")
            if url.startswith("/"):
                st["url"] = url
            else:
                m = re.match(r"^https?://([^/:?#]+)", url, re.I)
                if not m:
                    raise StepError(f"step {i}: sirf http(s) link")
                if base_host and not same_site(m.group(1), base_host):
                    raise StepError(f"step {i}: only your own site ({base_host}) ke pages")
                st["url"] = url
        if do in ("click", "fill", "select", "hover") or (do in ("screenshot", "scroll", "wait") and raw.get("target")):
            st["target"] = clean_target(raw.get("target") or {k: raw[k] for k in TARGET_KEYS if raw.get(k)})
        if do in ("fill", "select"):
            val = str(raw.get("value") if raw.get("value") is not None else "")[:200]
            why = secret_value(val)
            if why:
                raise StepError(f"step {i}: '{why}': I will not fill this value. Give a demo value (never a real OTP / password / card).")
            st["value"] = val
        if do == "press":
            key = str(raw.get("key") or raw.get("value") or "Enter").strip()
            if key not in KEYS:
                raise StepError(f"step {i}: key '{key}' is not allowed (only {', '.join(KEYS)})")
            st["key"] = key
        if do == "wait":
            st["ms"] = max(100, min(int(float(raw.get("ms") or raw.get("value") or 800)), 8000))
        if do == "scroll":
            st["y"] = max(-5000, min(int(float(raw.get("y") or raw.get("value") or 600)), 5000))
        if do == "screenshot" or raw.get("shot") or (do in ("click", "fill", "select") and raw.get("shot") is not False):
            shots += 1
            st["shot"] = True
            st["full"] = bool(raw.get("full"))
            st["alt"] = str(raw.get("alt") or "").strip()[:155]
        if raw.get("mask"):
            st["mask"] = [clean_target(m) for m in (raw["mask"] if isinstance(raw["mask"], list) else [raw["mask"]])][:10]
        out.append(st)
    if shots > MAX_SHOTS:
        raise StepError(f"no more than {MAX_SHOTS} screenshots in one flow")
    return out


def parse_step_line(line: str) -> dict[str, Any]:
    """'click "Save"', 'fill "Email" = demo@shop.in', 'goto /orders', 'press Enter', 'screenshot', 'wait 1000'."""
    s = (line or "").strip()
    m = re.match(r"^(\w+)\s*(.*)$", s)
    if not m:
        return {}
    do, rest = m.group(1).lower(), m.group(2).strip()
    aliases = {"open": "goto", "kholo": "goto", "dabao": "click", "tap": "click", "type": "fill", "likho": "fill", "bharo": "fill",
               "shot": "screenshot", "photo": "screenshot", "ruko": "wait", "key": "press"}
    do = aliases.get(do, do)
    q = re.findall(r'"([^"]+)"', rest)
    if do == "goto":
        return {"do": "goto", "url": rest.strip('"')}
    if do in ("click", "hover"):
        return {"do": do, "target": {"text": q[0] if q else rest}}
    if do in ("fill", "select"):
        val = rest.split("=", 1)[1].strip().strip('"') if "=" in rest else ""
        return {"do": do, "target": {"label": q[0] if q else rest.split("=", 1)[0].strip()}, "value": val}
    if do == "press":
        return {"do": "press", "key": rest or "Enter"}
    if do == "wait":
        return {"do": "wait", "ms": rest or 800}
    if do == "scroll":
        return {"do": "scroll", "y": rest or 600}
    if do == "screenshot":
        return {"do": "screenshot", "alt": q[0] if q else ""}
    return {"do": do}


def same_site(host: str, base: str) -> bool:
    h, b = (host or "").lower().strip("."), (base or "").lower().strip(".")
    if h == b:
        return True
    return h.endswith("." + b) or b.endswith("." + h) and h.count(".") >= 1 and b.split(".", 1)[-1] == h


def step_sentence(st: dict[str, Any], lang: str = "en") -> str:
    """One numbered step in plain words (imperative, UI label in bold), the way Google developer style writes procedures."""
    t = st.get("target") or {}
    label = t.get("name") or t.get("text") or t.get("label") or t.get("placeholder") or t.get("title") or t.get("alt") or ""
    b = f"**{label}**" if label else ""
    do = st["do"]
    hi = lang in ("hi", "hinglish")
    if st.get("note"):
        return st["note"]
    if do == "goto":
        path = st.get("url", "")
        return f"{path} kholiye." if hi else f"Open {path}."
    if do == "click":
        return (f"{b} par tap / click kijiye." if hi else f"Click {b}.") if b else ("Tap kijiye." if hi else "Click.")
    if do == "fill":
        return f"{b} mein apni jaankari likhiye." if hi else f"In {b}, enter your details."
    if do == "select":
        v = st.get("value") or ""
        return f"{b} mein **{v}** chuniye." if hi else f"In {b}, select **{v}**."
    if do == "press":
        return f"**{st['key']}** dabaiye." if hi else f"Press **{st['key']}**."
    if do == "hover":
        return f"{b} par pointer le jaaiye." if hi else f"Point to {b}."
    if do == "scroll":
        return "Neeche scroll kijiye." if hi else "Scroll down."
    return ""


# ---------------------------------------------------------------- privacy in screenshots
PII_PATTERNS = (r"[\w.+-]+@[\w-]+\.[\w.]{2,}", r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}", r"\b\d{4}\s\d{4}\s\d{4}\b",
                r"\b[A-Z]{5}\d{4}[A-Z]\b", r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
PII_JS_RX = "|".join(PII_PATTERNS)


def mask_text(text: str, keep: list[str] | None = None) -> str:
    """Personal data in TEXT that goes into docs: masked, except her own business contact lines she listed."""
    keep = [k for k in (keep or []) if k]

    def sub(m):
        v = m.group(0)
        return v if any(v.strip() in k or k in v for k in keep) else "[hataya]"
    return re.sub("|".join(f"(?:{p})" for p in PII_PATTERNS), sub, text or "")


# ---------------------------------------------------------------- style guide
AVOID = {  # word -> why (plain language + Google developer documentation style guide)
    "simply": "do not write 'simply / just / easy': it hurts a reader who finds it hard",
    "just": "do not write 'simply / just / easy'",
    "easily": "remove 'easily'",
    "obviously": "remove 'obviously'",
    "click here": "the link text should say where it goes (not 'click here')",
    "please note": "say it directly instead of 'please note'",
    "in order to": "'to' instead of 'in order to'",
    "utilize": "'use' instead of 'utilize'",
    "e.g.": "'for example' instead of 'e.g.'",
    "i.e.": "'that is' instead of 'i.e.'",
    "etc.": "the full list or 'and more' instead of 'etc.'",
    "kindly": "remove 'kindly' (go straight to 'Click...')",
}
PASSIVE = re.compile(r"\b(is|are|was|were|be|been|being)\s+(\w+ed|shown|done|made|given|sent|seen|written|taken)\b", re.I)


def blanks(text: str) -> list[str]:
    return re.findall(r"\[(?:blank|khaali|[^\]\n]{0,40}\?)\]", text or "", re.I)


def style_check(md: str, glossary: list[dict[str, str]] | None = None, lang: str = "en") -> dict[str, list[dict[str, str]]]:
    """Blocking: [blank] left, a secret, personal data, an image without alt. Warnings: long sentences, passive voice (English),
    words to avoid, her glossary's 'avoid' words, 'Image of' alt text, alt > 155 chars, numbered steps doing two things."""
    block: list[dict[str, str]] = []
    warn: list[dict[str, str]] = []
    text = md or ""
    for b in sorted(set(blanks(text)))[:8]:
        block.append({"kind": "blank", "text": f"Not filled in: {b}"})
    try:
        from ..net.policy import secret_found
        if secret_found(text):
            block.append({"kind": "secret", "text": "The docs contain something like a password / key / OTP: remove it"})
    except Exception:
        pass
    left = re.findall("|".join(f"(?:{p})" for p in PII_PATTERNS[2:]), text)
    if left:
        block.append({"kind": "pii", "text": "The docs contain a number like an Aadhaar / PAN / card: remove it"})
    for m in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", text):
        alt = m.group(1).strip()
        if not alt:
            block.append({"kind": "alt", "text": f"Screenshot without alt text: {m.group(2)[:40]}"})
        elif len(alt) > 155:
            warn.append({"kind": "alt", "text": f"Alt text longer than 155 characters: {alt[:40]}..."})
        elif re.match(r"(image|photo|picture|screenshot)\s+of\b", alt, re.I):
            warn.append({"kind": "alt", "text": f"Do not start alt text with 'Image of': {alt[:40]}"})
    plain = re.sub(r"```.*?```", " ", text, flags=re.S)
    plain = re.sub(r"!\[[^\]]*\]\([^)]*\)|`[^`]*`", " ", plain)
    low = plain.lower()
    for w, why in AVOID.items():
        if re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", low):
            warn.append({"kind": "word", "text": f"'{w}': {why}"})
    for g in glossary or []:
        av = (g.get("avoid") or "").strip()
        if av and re.search(r"(?<!\w)" + re.escape(av.lower()) + r"(?!\w)", low):
            warn.append({"kind": "glossary", "text": f"'{av}': write '{g.get('term') or g.get('use')}' instead (your glossary)"})
    long_n = 0
    for sent in re.split(r"(?<=[.!?।])\s+|\n", plain):
        words = re.findall(r"\w+", sent)
        if len(words) > 25 and long_n < 4:
            long_n += 1
            warn.append({"kind": "long", "text": f"Long sentence ({len(words)} words): {sent.strip()[:60]}..."})
    if lang == "en":
        pas = PASSIVE.findall(plain)
        if len(pas) >= 3:
            warn.append({"kind": "passive", "text": f"{len(pas)} places use the passive voice ('{' '.join(pas[0])}'): say directly who does what"})
    for line in plain.splitlines():
        if re.match(r"^\s*\d+\.\s", line) and re.search(r"\b(and then|then)\b|, phir |, aur phir ", line, re.I):
            warn.append({"kind": "step", "text": f"Two actions in one step: {line.strip()[:60]}"})
            break
    return {"blocking": block, "warnings": warn[:20]}


# ---------------------------------------------------------------- translation lock (names / numbers / UI labels / code stay)
def lock(text: str, keep: list[str] | None = None) -> tuple[str, dict[str, str]]:
    """Code blocks, inline code, **UI labels**, image links, URLs, numbers and her keep-words become ⟦n⟧ markers."""
    table: dict[str, str] = {}
    keep = sorted({k for k in (keep or []) if k}, key=len, reverse=True)
    pats = [r"```.*?```", r"`[^`\n]+`", r"!\[[^\]]*\]\([^)]+\)", r"\]\([^)]+\)", r"\*\*[^*\n]+\*\*"] + [re.escape(k) for k in keep] + [
        r"https?://\S+", r"[\w.+-]+@[\w-]+\.[\w.]+", r"(?:₹|Rs\.?|INR)\s?[\d,]+(?:\.\d+)?", r"\bv?\d+(?:[.,/:-]\d+)*\b"]
    rx = re.compile("|".join(f"(?:{p})" for p in pats), re.S | re.I)

    def sub(m):
        key = f"⟦{len(table) + 1}⟧"
        table[key] = m.group(0)
        return key
    return rx.sub(sub, text or ""), table


def unlock(text: str, table: dict[str, str]) -> tuple[str, list[str]]:
    lost = []
    for k, v in table.items():
        if k in text:
            text = text.replace(k, v, 1)
        else:
            lost.append(v)
    return re.sub(r"⟦\d+⟧", "", text), lost


# ---------------------------------------------------------------- research behind the design (Oct 2026)
SOURCES = [
    {"what": "Diataxis: four kinds of docs (tutorial, how-to, reference, explanation) for four user needs (Daniele Procida)",
     "url": "https://diataxis.fr/", "seen": "2026-10-23"},
    {"what": "Canonical moved its docs to Diataxis", "url": "https://ubuntu.com/blog/diataxis-a-new-foundation-for-canonical-documentation",
     "seen": "2026-10-23"},
    {"what": "Google developer documentation style guide, images: crop tight, one visual style, hide personal data with a solid 100% "
             "opaque box (blur / mosaic can be reversed), no screenshots of text / code, alt text <= 155 chars, no 'Image of', "
             "numbered callouts; page last updated 2026-10-09", "url": "https://developers.google.com/style/images", "seen": "2026-10-23"},
    {"what": "digital.gov plain language guide: active voice, present tense, short words and sections, address the reader",
     "url": "https://digital.gov/guides/plain-language/writing", "seen": "2026-10-23"},
    {"what": "GIGW 3.0 (Guidelines for Indian Government Websites and Apps): WCAG 2.1 AA, content in Indian languages",
     "url": "https://www.skynettechnologies.com/blog/gigw-3-0-government-website-accessibility-in-india", "seen": "2026-10-23"},
    {"what": "Docs drift: docs go stale when the product changes; tie docs to code / releases and check on every change",
     "url": "https://www.mintlify.com/library/how-to-stop-documentation-drift", "seen": "2026-10-23"},
    {"what": "GitHub REST: generate release notes (POST /repos/{owner}/{repo}/releases/generate-notes needs Contents: write; Hoola "
             "stays read-only and builds notes from merged pull requests instead), API version header 2026-03-10",
     "url": "https://docs.github.com/en/rest/releases/releases#generate-release-notes-content-for-a-release", "seen": "2026-10-23"},
    {"what": "OpenAPI 3.2.0 (Sept 2025) alongside 3.1 / 3.0 / Swagger 2.0", "url": "https://en.wikipedia.org/wiki/OpenAPI_Specification",
     "seen": "2026-10-23"},
]
