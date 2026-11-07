"""Item 8b: a tiny step script compiled to JavaScript. Hand-built (the port law).

crawl4ai ships C4A-Script - a Lark-grammar DSL that compiles to `js_code` and has no runtime of its own.
The useful part is the shape, not the grammar: a short, readable, REVIEWABLE list of steps that a page
needs before its content exists (accept the notice, open the tab, scroll the list), which a model can
write and a person can read.

Hoola's existing doors do clicks already (`browse_web`, the Computer Operator) but they are driven turn by
turn by the model. This compiles a whole sequence ONCE, so a scrape that needs three clicks is one fetch
with a script attached rather than three model turns.

Safety is the whole design here, because this takes text and produces code:

  * every selector and value is embedded as a JSON literal, never concatenated into source, so a quote or
    a `</script>` in a selector cannot escape its string;
  * the command set is CLOSED - six verbs, no `EVAL`, no arbitrary JS passthrough. crawl4ai's DSL has an
    EVAL command; a DSL that can run arbitrary JS is just JS with extra steps, and the point of compiling
    is that the result can be reviewed;
  * TYPE refuses a password/OTP/CVV/card field by name, so this can never be the thing that types a
    credential into a page - that rule is Hoola's, and it belongs in the compiler rather than in a caller's
    good intentions;
  * numbers are bounded and the whole script has a step cap and a total-time cap.

Verbs:  WAIT <css> [seconds] | WAIT <seconds> | CLICK <css> | TYPE <css> <text>
        SCROLL <pixels|bottom> | SUBMIT <css>
"""
from __future__ import annotations

import json
import re


def _js(value) -> str:
    """A JSON literal safe to embed even inside an HTML <script> block.

    json.dumps does not escape `/`, so a value containing `</script>` would close the tag and everything
    after it would be parsed as HTML. Escaping `<` and `>` as \u003c/\u003e costs nothing and removes the
    whole class of problem, wherever the emitted script ends up.
    """
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e")
from dataclasses import dataclass, field

MAX_STEPS = 25
MAX_WAIT_S = 30
MAX_TOTAL_S = 90
# A field whose name/id/type says credential is never typed into by a script. Hoola's rule, enforced here.
_SECRET_FIELD = re.compile(r"pass|pwd|otp|cvv|cvc|pin\b|card.?number|cardno|secret|token|security.?code", re.I)
_VERBS = {"WAIT", "CLICK", "TYPE", "SCROLL", "SUBMIT"}


class StepError(ValueError):
    """Raised at COMPILE time, with the line number, so a bad script never reaches a browser."""


@dataclass
class Step:
    verb: str
    css: str = ""
    value: str = ""
    seconds: float = 0.0
    pixels: int = 0
    line: int = 0


@dataclass
class Script:
    steps: list[Step] = field(default_factory=list)
    js: str = ""
    total_s: float = 0.0
    warnings: list[str] = field(default_factory=list)


def _num(tok: str, line: int) -> float:
    try:
        return float(tok)
    except ValueError:
        raise StepError(f"line {line}: {tok!r} is not a number")


def _strip_comment(raw: str) -> str:
    """A `#` starts a comment only OUTSIDE quotes.

    The first version used raw.split("#", 1)[0], which cut `TYPE "#q" "cement"` down to `TYPE "` - and a
    CSS id selector always contains a #, so that broke the commonest selector form there is.
    """
    out, q = [], ""
    for ch in raw:
        if q:
            out.append(ch)
            if ch == q:
                q = ""
            continue
        if ch in ('"', "'"):
            q = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out)


def parse(src: str) -> list[Step]:
    """One step per line. `#` outside quotes starts a comment. Quoted values keep their spaces."""
    steps: list[Step] = []
    for i, raw in enumerate((src or "").splitlines(), 1):
        line = _strip_comment(raw).strip()
        if not line:
            continue
        if len(steps) >= MAX_STEPS:
            raise StepError(f"line {i}: more than {MAX_STEPS} steps")
        # verb, then either a quoted string or a bare token, then an optional rest
        m = re.match(r'^([A-Za-z]+)\s*(?:"([^"]*)"|(\S+))?\s*(.*)$', line)
        if not m:
            raise StepError(f"line {i}: cannot read {line!r}")
        verb = m.group(1).upper()
        first = m.group(2) if m.group(2) is not None else (m.group(3) or "")
        rest = (m.group(4) or "").strip()
        if verb not in _VERBS:
            raise StepError(f"line {i}: unknown command {verb!r}; allowed: {', '.join(sorted(_VERBS))}")
        if verb == "WAIT":
            if not first:
                raise StepError(f"line {i}: WAIT needs a selector or a number of seconds")
            if re.match(r"^\d+(?:\.\d+)?$", first):
                steps.append(Step("WAIT", seconds=min(MAX_WAIT_S, _num(first, i)), line=i))
            else:
                if rest and not re.match(r"^\d+(?:\.\d+)?$", rest):
                    raise StepError(f"line {i}: WAIT takes a selector and an optional number of seconds; "
                                    f"{rest[:40]!r} is neither")
                secs = min(MAX_WAIT_S, _num(rest, i)) if rest else 10.0
                steps.append(Step("WAIT", css=first, seconds=secs, line=i))
        elif verb in ("CLICK", "SUBMIT"):
            if not first:
                raise StepError(f"line {i}: {verb} needs a selector")
            if rest:
                # Refuse, never truncate. `CLICK "a" ); alert(1); //"` parsed as selector `a` with the
                # remainder silently dropped - nothing was injected, but the step did something other
                # than what was written, and a selector that quietly changes is its own bug.
                raise StepError(f"line {i}: {verb} takes only a selector; {rest[:40]!r} is left over - "
                                f"if the selector contains a quote, it cannot be written here")
            steps.append(Step(verb, css=first, line=i))
        elif verb == "TYPE":
            if not first or not rest:
                raise StepError(f"line {i}: TYPE needs a selector and a value")
            if _SECRET_FIELD.search(first):
                raise StepError(f"line {i}: this script may not type into {first!r} - a password, OTP, PIN, "
                                f"CVV or card field is never filled by an automated step")
            val = rest[1:-1] if (len(rest) >= 2 and rest[0] == rest[-1] == '"') else rest
            steps.append(Step("TYPE", css=first, value=val, line=i))
        else:                                   # SCROLL
            if not first:
                raise StepError(f"line {i}: SCROLL needs a pixel count or 'bottom'")
            if rest:
                raise StepError(f"line {i}: SCROLL takes one value; {rest[:40]!r} is left over")
            if first.lower() == "bottom":
                steps.append(Step("SCROLL", value="bottom", line=i))
            else:
                steps.append(Step("SCROLL", pixels=int(min(100_000, max(-100_000, _num(first, i)))), line=i))
    if not steps:
        raise StepError("the script has no steps")
    return steps


def compile_js(src: str) -> Script:
    """Steps -> one async IIFE. Every selector and value goes in as a JSON literal."""
    steps = parse(src)
    total = 0.0
    body: list[str] = [
        "const $=(s)=>document.querySelector(s);",
        "const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));",
        "const waitFor=async(s,ms)=>{const t=Date.now();while(Date.now()-t<ms){if($(s))return true;"
        "await sleep(100);}return false;};",
        "const done=[];",
    ]
    for st in steps:
        sel = _js(st.css)
        if st.verb == "WAIT" and not st.css:
            total += st.seconds
            body.append(f"await sleep({int(st.seconds * 1000)}); done.push(['WAIT',{st.seconds}]);")
        elif st.verb == "WAIT":
            total += st.seconds
            body.append(f"done.push(['WAIT',{sel},await waitFor({sel},{int(st.seconds * 1000)})]);")
        elif st.verb == "CLICK":
            body.append(f"{{const e=$({sel}); if(e){{e.click(); done.push(['CLICK',{sel},true]);}}"
                        f"else{{done.push(['CLICK',{sel},false]);}} await sleep(250);}}")
        elif st.verb == "SUBMIT":
            body.append(f"{{const e=$({sel}); if(e){{(e.form||e).submit?.(); "
                        f"done.push(['SUBMIT',{sel},true]);}}else{{done.push(['SUBMIT',{sel},false]);}} "
                        f"await sleep(500);}}")
        elif st.verb == "TYPE":
            val = _js(st.value)
            body.append(f"{{const e=$({sel}); if(e){{e.focus(); e.value={val}; "
                        f"e.dispatchEvent(new Event('input',{{bubbles:true}})); "
                        f"e.dispatchEvent(new Event('change',{{bubbles:true}})); "
                        f"done.push(['TYPE',{sel},true]);}}else{{done.push(['TYPE',{sel},false]);}}}}")
        else:
            if st.value == "bottom":
                body.append("window.scrollTo(0,document.body.scrollHeight); "
                            "done.push(['SCROLL','bottom']); await sleep(400);")
            else:
                body.append(f"window.scrollBy(0,{st.pixels}); done.push(['SCROLL',{st.pixels}]); "
                            f"await sleep(300);")
    total = min(total, MAX_TOTAL_S)
    js = "(async()=>{" + "".join(body) + "return done;})()"
    warn = []
    if total >= MAX_TOTAL_S:
        warn.append(f"waits add up to the {MAX_TOTAL_S}s cap")
    return Script(steps=steps, js=js, total_s=round(total, 2), warnings=warn)
