"""v0.132: what the model is told when it writes one Compose screen (the kit's real API is read from the kit files)."""
from __future__ import annotations

import re
from functools import lru_cache

from .gen import TEMPLATE, kotlin_name


SKIP = {"t", "digits", "spec", "typeOf", "arrList", "AppBar", "TopTabs", "FloatingPill", "Fab", "AppShell",
        "HoolaTheme", "onCreate", "Screens", "BottomBar", "load", "apply", "init", "refresh", "openDrawer", "get", "put", "DemoNote"}


def signatures(src: str) -> list[str]:
    """Public functions with their real parameter lists; members of objects get the object's name (AppData.list...)."""
    out: list[str] = []
    i, n = 0, len(src)
    stack: list[tuple[str, int]] = []           # (object / class name, brace depth where it opened)
    depth = 0
    pending: str | None = None
    tok = re.compile(r"(@Composable\s+)?((?:private|internal|override)\s+)?fun\s+(<[^>]+>\s+)?([\w.]+)\s*\(|"
                     r"\b(?:object|class)\s+(\w+)|[{}]|\"(?:\\.|[^\"\\])*\"")
    while True:
        m = tok.search(src, i)
        if not m:
            break
        t = m.group(0)
        if t == "{":
            depth += 1
            if pending:
                stack.append((pending, depth))
                pending = None
            i = m.end()
            continue
        if t == "}":
            if stack and stack[-1][1] == depth:
                stack.pop()
            depth -= 1
            i = m.end()
            continue
        if t.startswith('"'):
            i = m.end()
            continue
        if m.group(5):
            pending = m.group(5)
            i = m.end()
            continue
        # a function: balance its parentheses
        j, d = m.end(), 1
        while j < n and d:
            if src[j] == "(":
                d += 1
            elif src[j] == ")":
                d -= 1
            j += 1
        args = re.sub(r"\s+", " ", src[m.end() - 1:j])
        k = j
        ret = ""
        mm = re.match(r"\s*:\s*([\w<>?, .()@\->]+?)\s*(?=[{=]|\n)", src[k:])
        if mm:
            ret = mm.group(1).strip()
        name = m.group(4)
        private = bool(m.group(2)) and "private" in m.group(2)
        owner = stack[-1][0] if stack else ""
        i = j
        if private or name in SKIP or name.split(".")[-1] in SKIP or owner in ("Strings",):
            continue
        if owner and owner not in ("AppData", "AppState", "Act", "Nav", "Item"):
            continue
        pre = f"{owner}." if owner and owner != "Item" else ("item." if owner == "Item" else "")
        line = f"{'@Composable ' if m.group(1) else ''}{pre}{name}{args}" + (f": {ret}" if ret and ret != "Unit" else "")
        if line not in out:
            out.append(line)
    return out


@lru_cache(maxsize=1)
def kit_sheet() -> str:
    """Every public kit function / object member, one line each, straight from the Kotlin source."""
    kit = TEMPLATE / "app/src/main/java/hoola/kit"
    lines: list[str] = []
    for name in ("Kit.kt", "Data.kt", "Actions.kt", "Nav.kt", "Theme.kt"):
        for ln in signatures((kit / name).read_text()):
            if ln not in lines:
                lines.append(ln)
    return "\n".join(lines)


SCREEN_SYSTEM = """You write ONE screen of a native Android app in Kotlin + Jetpack Compose, from its approved web design.
The project around it is fixed and already compiles: theme, navigation, icons, data, actions and the component kit
"HoolaKit" (package hoola.kit). You only write this one file. It must compile on the first try.

FILE CONTRACT
- First line: package hoola.app.screens
- Imports: only androidx.compose.foundation.*, androidx.compose.material3.*, androidx.compose.runtime.*,
  androidx.compose.ui.*, androidx.compose.animation.*, kotlin.math.*, and hoola.kit.* (always: import hoola.kit.*).
  Import exactly what you use (Modifier, dp, Alignment, Arrangement, layouts like Row / Column / Box, fillMaxWidth,
  padding, getValue / setValue, remember, mutableStateOf...). Do NOT import androidx.compose.material.* (Material 2) or
  material icons; icons are HIcon("name") / IconBtn("name", ...) with the icon names listed below.
- Exactly one public function: @Composable fun {FN}() with NO parameters. Private @Composable helpers are fine. No classes,
  no objects, no top-level vals with state.
- Wrap the screen in Page(title = ..., back = {BACK}) { ... }. Page's body is a LazyListScope: put every visual piece in
  block { ... } (or items(...) / item { ... }). Composable calls must be inside block { }, never directly in the body.
  Page's bottomBar = { ... } (a RowScope) is for a sticky bottom action (Checkout, Book now, Submit).
- Navigation: val nav = LocalNav.current; nav.go("screen_id"), nav.open("screen_id", "list", record.id) (opens a record),
  nav.back(). Use ONLY these screen ids: {IDS}.
- Data: AppData.list("name") -> List<Item>; AppData.facts (Item); AppState.current("list") = the record opened with
  nav.open; Item has .id, .name, .price, .s("key"), .n("key"), .i("key"), .b("key"), .list("key"), .strings("key").
  Lists that exist (name: keys): {LISTS}. Business facts keys: {FACTS}.
  Cart: AddButton(item.id), AppState.cartCount, AppState.cartItems("products"), AppState.cartTotal("products"),
  rupees(amount). Form values: Field(label, key) stores in AppState.form[key].
- Actions: val c = ctx(); Act.call(c), Act.whatsapp(c, text), Act.share(c, text), Act.maps(c), Act.payUpi(c, amount, note)
  (opens the customer's own UPI app to the business's UPI ID), Act.toast(c, text), Act.copy(c, text, said).
- Look: colours H.c.primary / accent / ink / muted / surface / bg / tint / line / primaryText / accentText; type
  H.t.display / h1 / h2 / title / body / small / label / price. Never hard-code colours or font sizes; never use dark /
  light checks (the theme does both).
- Words: in {LANG}. Real facts only (from AppData.facts / lists); a missing fact = Blank("what") or FactText(key, what).

NEVER
- password, PIN, OTP-for-payment, card number, CVV, UPI PIN fields or text; no PasswordVisualTransformation.
- network, files, Intent, WebView, reflection, logging, SharedPreferences, NavHost, ViewModel, Hilt, Room.
- deprecated / experimental APIs that need opt-in (no @OptIn), no Material 2.

MATCH THE DESIGN: same sections in the same order, same hierarchy, same words, same actions; it should feel native
(tap ripples come from the kit). Keep it under ~250 lines.

HOOLAKIT (exact signatures, use them as written):
{KIT}

ICONS: {ICONS}

Answer with JSON only: {"kotlin": "<the whole file>", "notes": "<one line>"}"""

FIX_SYSTEM = """You fix ONE Kotlin + Jetpack Compose screen file that did not compile (or broke a house rule). Same contract as
before (package hoola.app.screens, only the allowed imports, one @Composable fun {FN}() with no parameters, HoolaKit
components, Page { block { } } body, ids {IDS}). Fix EVERY listed error; change nothing else. If a kit call is wrong, check
its exact signature below. Prefer simple, certain code over clever code.

HOOLAKIT:
{KIT}

Answer with JSON only: {"kotlin": "<the whole fixed file>", "notes": "<what you fixed>"}"""


def fill(tpl: str, **kw: str) -> str:
    out = tpl
    for k, v in kw.items():
        out = out.replace("{" + k + "}", v)
    return out


def screen_system(sid: str, back: bool, ids: list[str], lists: dict[str, list[str]], facts: list[str], lang: str,
                  icons: list[str]) -> str:
    return fill(SCREEN_SYSTEM, FN=kotlin_name(sid), BACK="true" if back else "false", IDS=", ".join(ids),
                LISTS="; ".join(f"{k}: {', '.join(v)}" for k, v in lists.items()) or "(none)",
                FACTS=", ".join(facts) or "(none)", LANG=lang, KIT=kit_sheet(), ICONS=", ".join(sorted(icons)))


def fix_system(sid: str, ids: list[str]) -> str:
    return fill(FIX_SYSTEM, FN=kotlin_name(sid), IDS=", ".join(ids), KIT=kit_sheet())
