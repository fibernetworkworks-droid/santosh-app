"""Local checks for WhatsApp message templates, run before anything goes to Meta.

These catch the common reasons Meta rejects a template, so Santosh can fix the draft
himself instead of waiting for a rejection."""
from __future__ import annotations

import re

NAME_RE = re.compile(r"^[a-z0-9_]{1,512}$")
VAR_RE = re.compile(r"\{\{\s*(\d+)\s*\}\}")
CATEGORIES = {"MARKETING", "UTILITY", "AUTHENTICATION"}
LANGUAGES = {"en", "en_US", "en_GB", "hi", "mr", "gu", "ta", "te", "kn", "ml", "bn", "pa", "ur"}


def check_template(name: str, language: str, category: str, body: str,
                   example_values: list[str] | None = None, footer: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    example_values = list(example_values or [])

    if not NAME_RE.match(name or ""):
        errors.append("Template name must use only lowercase letters, numbers and underscores (e.g. diwali_offer_2026).")
    if language not in LANGUAGES:
        errors.append(f"Language '{language}' is not one Santosh supports. Use one of: {', '.join(sorted(LANGUAGES))}.")
    if (category or "").upper() not in CATEGORIES:
        errors.append("Category must be MARKETING, UTILITY or AUTHENTICATION. Offers and promotions are MARKETING.")
    body = body or ""
    if not body.strip():
        errors.append("Body text is empty.")
    if len(body) > 1024:
        errors.append(f"Body is {len(body)} characters; WhatsApp allows at most 1024.")
    if footer and len(footer) > 60:
        errors.append(f"Footer is {len(footer)} characters; WhatsApp allows at most 60.")
    if footer and VAR_RE.search(footer):
        errors.append("Footer cannot contain variables like {{1}}.")

    nums = [int(n) for n in VAR_RE.findall(body)]
    distinct = sorted(set(nums))
    if distinct and distinct != list(range(1, len(distinct) + 1)):
        errors.append("Variables must be numbered in order starting at {{1}}, with no gaps.")
    if re.search(r"\{\{[^}]*\}\}", VAR_RE.sub("", body)):
        errors.append("Variables must look exactly like {{1}}, {{2}} (numbers only).")
    if re.search(r"\}\}\s*\{\{", body):
        errors.append("Two variables cannot sit next to each other; put words between them.")
    stripped = body.strip()
    if stripped.startswith("{{") or stripped.endswith("}}"):
        errors.append("The body cannot start or end with a variable. Add words before/after it.")
    if len(example_values) != len(distinct):
        errors.append(f"Give one example value for each variable: {len(distinct)} variables, {len(example_values)} examples.")
    if any(not str(v).strip() for v in example_values):
        errors.append("Example values cannot be empty.")
    if re.search(r"\n{3,}", body):
        errors.append("Body cannot contain more than two line breaks in a row.")
    if re.search(r" {5,}|\t", body):
        errors.append("Body cannot contain tabs or more than four spaces in a row.")

    words = len(re.findall(r"\w+", VAR_RE.sub("", body)))
    if distinct and words < 3 * len(distinct) + 3:
        warnings.append("Too many variables for such a short message; Meta often rejects this. Add more fixed text.")
    if (category or "").upper() == "MARKETING" and not re.search(r"(stop|unsubscribe|band karne|opt.?out)", body + " " + (footer or ""), re.I):
        warnings.append("Add an opt-out line such as 'STOP likhkar bhejein' in the footer. It reduces blocks and reports.")
    if re.search(r"(bit\.ly|tinyurl|goo\.gl)", body, re.I):
        warnings.append("Link shorteners get templates rejected. Use the full website link.")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "variables": len(distinct)}


def render_body(body: str, values: list[str]) -> str:
    def rep(m):
        i = int(m.group(1)) - 1
        return values[i] if 0 <= i < len(values) else m.group(0)
    return VAR_RE.sub(rep, body)
