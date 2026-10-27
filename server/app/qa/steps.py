"""The safe step language of the QA Sahayak. A test case is a short JSON list of these steps; the model may only WRITE such
lists (never JavaScript), and every list is checked here before it is stored or run.

  {"do": "goto", "path": "/contact/"}                       same site only (path, or a full URL on her verified host)
  {"do": "click", "target": {...}}                         target = {text} | {role, name} | {label} | {placeholder} | {testid} | {alt} | {css}
  {"do": "fill", "target": {...}, "value": "Ramesh"}       value may be {account.username} / {account.password} / {rand.email} / {rand.phone}
  {"do": "select", "target": {...}, "value": "Pune"}
  {"do": "check" | "uncheck" | "hover", "target": {...}}
  {"do": "press", "key": "Enter"}                          keys from KEYS only
  {"do": "expect_text" | "expect_no_text", "text": "..."}
  {"do": "expect_visible" | "expect_hidden" | "expect_enabled" | "expect_disabled" | "expect_invalid" | "expect_valid", "target": {...}}
  {"do": "expect_url", "contains": "/thanks"}   {"do": "expect_title", "contains": "..."}
  {"do": "viewport", "width": 360}   {"do": "wait", "ms": 800}   {"do": "back"}   {"do": "screenshot", "name": "home"}
  {"do": "audit", "kind": "a11y" | "overflow" | "links" | "console" | "headers" | "images"}
"""
from __future__ import annotations

import re
from typing import Any

OPS = ("goto", "click", "fill", "select", "check", "uncheck", "hover", "press", "expect_text", "expect_no_text", "expect_visible",
       "expect_hidden", "expect_enabled", "expect_disabled", "expect_invalid", "expect_valid", "expect_url", "expect_title",
       "viewport", "wait", "back", "screenshot", "audit")
TARGET_OPS = ("click", "fill", "select", "check", "uncheck", "hover", "expect_visible", "expect_hidden", "expect_enabled",
              "expect_disabled", "expect_invalid", "expect_valid")
TARGET_KEYS = ("text", "role", "name", "label", "placeholder", "testid", "alt", "css", "exact")
ROLES = ("button", "link", "textbox", "checkbox", "radio", "combobox", "heading", "img", "navigation", "tab", "listitem", "menuitem",
         "dialog", "alert", "switch", "searchbox", "option", "region", "banner", "contentinfo", "main", "form", "spinbutton")
KEYS = ("Enter", "Tab", "Escape", "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Space", "Backspace", "Home", "End", "PageDown",
        "PageUp", "Shift+Tab")
AUDITS = ("a11y", "overflow", "links", "console", "headers", "images")
WIDTHS = (320, 360, 390, 412, 768, 1024, 1280, 1440)
PLACEHOLDERS = re.compile(r"\{(account\.(?:username|password)|rand\.(?:email|phone|name|text))\}")
MAX_STEPS = 40


def _clean_target(t: Any) -> tuple[dict[str, Any] | None, str]:
    if isinstance(t, str):
        t = {"text": t}
    if not isinstance(t, dict):
        return None, "target missing"
    out: dict[str, Any] = {}
    for k in TARGET_KEYS:
        if k in t and t[k] not in (None, ""):
            out[k] = bool(t[k]) if k == "exact" else str(t[k])[:160]
    if "role" in out and out["role"] not in ROLES:
        return None, f"role '{out['role']}' not allowed"
    css = out.get("css")
    if css is not None:
        low = css.lower()
        if len(css) > 160 or "javascript" in low or "\\" in css or "url(" in low or ">>" in css or "xpath" in low or low.startswith("/"):
            return None, "css selector not allowed"
    if not any(k in out for k in ("text", "role", "label", "placeholder", "testid", "alt", "css")):
        return None, "target needs text / role / label / placeholder / testid / alt / css"
    return out, ""


def clean_step(s: Any) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(s, dict):
        return None, "a step must be an object"
    op = str(s.get("do") or s.get("op") or "").strip().lower()
    if op not in OPS:
        return None, f"step '{op}' is not in the step language"
    out: dict[str, Any] = {"do": op}
    if op in TARGET_OPS:
        t, why = _clean_target(s.get("target"))
        if not t:
            return None, f"{op}: {why}"
        out["target"] = t
    if op == "goto":
        p = str(s.get("path") or s.get("url") or "/").strip()
        if p.lower().startswith(("javascript:", "data:", "file:", "about:", "chrome:", "blob:", "view-source:")):
            return None, "goto: only pages of the site"
        out["path"] = p[:400]
    elif op in ("fill", "select"):
        v = s.get("value")
        if v is None:
            return None, f"{op}: value missing"
        out["value"] = str(v)[:500]
    elif op == "press":
        k = str(s.get("key") or "")
        if k not in KEYS:
            return None, f"press: key '{k}' not allowed"
        out["key"] = k
    elif op in ("expect_text", "expect_no_text"):
        tx = str(s.get("text") or "").strip()
        if not tx:
            return None, f"{op}: text missing"
        out["text"] = tx[:300]
    elif op in ("expect_url", "expect_title"):
        c = str(s.get("contains") or s.get("text") or "")
        out["contains"] = c[:300]
    elif op == "viewport":
        try:
            w = int(s.get("width") or 0)
        except (TypeError, ValueError):
            w = 0
        if w not in WIDTHS:
            return None, f"viewport: width one of {WIDTHS}"
        out["width"] = w
    elif op == "wait":
        try:
            out["ms"] = max(50, min(5000, int(s.get("ms") or 500)))
        except (TypeError, ValueError):
            out["ms"] = 500
    elif op == "screenshot":
        out["name"] = re.sub(r"[^\w-]", "_", str(s.get("name") or "shot"))[:40]
    elif op == "audit":
        k = str(s.get("kind") or "")
        if k not in AUDITS:
            return None, f"audit: kind one of {AUDITS}"
        out["kind"] = k
    if s.get("note"):
        out["note"] = str(s["note"])[:200]
    return out, ""


def clean(steps: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """(steps that passed, problems). A list with any problem should not be run as it is."""
    if not isinstance(steps, list):
        return [], ["steps must be a list"]
    good, bad = [], []
    for i, s in enumerate(steps[:MAX_STEPS]):
        c, why = clean_step(s)
        if c:
            good.append(c)
        else:
            bad.append(f"step {i + 1}: {why}")
    if len(steps) > MAX_STEPS:
        bad.append(f"max {MAX_STEPS} steps")
    return good, bad


def _t(t: dict[str, Any]) -> str:
    if "role" in t:
        return f"{t['role']} '{t.get('name', '')}'".strip()
    for k in ("label", "placeholder", "text", "alt", "testid", "css"):
        if k in t:
            return f"{k} '{t[k]}'" if k != "text" else f"'{t[k]}'"
    return "?"


def describe(s: dict[str, Any]) -> str:
    """A plain line for the person reading the case / bug (never shows a test account's real value)."""
    op = s["do"]
    tg = _t(s.get("target") or {})
    v = s.get("value", "")
    if "{account.password}" in v:
        v = "(test password)"
    elif "{account.username}" in v:
        v = "(test username)"
    return {
        "goto": f"Kholo {s.get('path')}", "click": f"Click: {tg}", "fill": f"Bharo {tg}: {v}", "select": f"Chuno {tg}: {v}",
        "check": f"Tick: {tg}", "uncheck": f"Tick hatao: {tg}", "hover": f"Mouse le jao: {tg}", "press": f"Key: {s.get('key')}",
        "expect_text": f"Dikhna chahiye: \"{s.get('text')}\"", "expect_no_text": f"Nahi dikhna chahiye: \"{s.get('text')}\"",
        "expect_visible": f"Dikhe: {tg}", "expect_hidden": f"Chhupa ho: {tg}", "expect_enabled": f"Chalu ho: {tg}",
        "expect_disabled": f"Band ho: {tg}", "expect_invalid": f"Galat maana jaaye: {tg}", "expect_valid": f"Sahi maana jaaye: {tg}",
        "expect_url": f"Address mein ho: {s.get('contains')}", "expect_title": f"Title mein ho: {s.get('contains')}",
        "viewport": f"Screen chaudai {s.get('width')} px", "wait": f"Ruko {s.get('ms')} ms", "back": "Peeche jao",
        "screenshot": f"Screenshot: {s.get('name')}", "audit": f"Jaanch: {s.get('kind')}",
    }.get(op, op)


GUIDE = __doc__ or ""
