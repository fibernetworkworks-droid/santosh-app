"""Her text in Markdown -> Google Docs changes (Docs API batchUpdate requests).

Supported: # .. ###### headings, 'Title:' / 'Subtitle:' lines, **bold**, *italic* / _italic_, ~~strike~~, <u>under</u>,
`code`, [links](https://...), - / * bullets, 1. numbered lists, - [ ] / - [x] checklists (two spaces or a tab = one
level deeper), > quotes, ``` code blocks, | tables |, ![alt](picture), and a line '---page---' for a page break.
A plain '---' line has no Docs API request (Google cannot insert a horizontal line); it is skipped and said."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .model import u16

MONO = "Roboto Mono"
HEADINGS = {1: "HEADING_1", 2: "HEADING_2", 3: "HEADING_3", 4: "HEADING_4", 5: "HEADING_5", 6: "HEADING_6"}


@dataclass
class Block:
    kind: str                      # text | table | image | page
    paras: list = field(default_factory=list)     # text: [(style, text, spans, bullet(kind, level) | None, extra)]
    rows: list = field(default_factory=list)      # table
    src: str = ""                                 # image
    alt: str = ""


INLINE = re.compile(r"(\*\*(?P<b>.+?)\*\*|__(?P<b2>.+?)__|~~(?P<s>.+?)~~|<u>(?P<u>.+?)</u>|`(?P<c>[^`]+)`|"
                    r"\[(?P<lt>[^\]]+)\]\((?P<lu>[^)\s]+)\)|(?<![\w*])\*(?P<i>[^*\s][^*]*?)\*(?!\w)|(?<![\w_])_(?P<i2>[^_\s][^_]*?)_(?!\w))")


def inline(text: str) -> tuple[str, list[tuple[int, int, dict]]]:
    """Plain text + style spans (UTF-16 offsets inside the paragraph)."""
    out, spans, pos = [], [], 0
    cur = 0
    for m in INLINE.finditer(text):
        before = text[pos:m.start()]
        out.append(before)
        cur += u16(before)
        g = m.groupdict()
        inner = next(v for k, v in g.items() if v is not None and k != "lu")
        style: dict = {}
        if g["b"] is not None or g["b2"] is not None:
            style = {"bold": True}
        elif g["s"] is not None:
            style = {"strikethrough": True}
        elif g["u"] is not None:
            style = {"underline": True}
        elif g["c"] is not None:
            style = {"weightedFontFamily": {"fontFamily": MONO}}
        elif g["lt"] is not None:
            inner = g["lt"]
            url = g["lu"]
            if re.match(r"^(https?://|mailto:)", url, re.I):
                style = {"link": {"url": url}}
        elif g["i"] is not None or g["i2"] is not None:
            style = {"italic": True}
        # nested bold-in-link etc.: one level of nesting, the inner text parsed again
        sub, subspans = inline(inner) if (g["c"] is None and inner != text) else (inner, [])
        out.append(sub)
        n = u16(sub)
        if style:
            spans.append((cur, cur + n, style))
        spans += [(cur + a, cur + b, s) for a, b, s in subspans]
        cur += n
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), spans


def parse(md: str) -> tuple[list[Block], list[str]]:
    notes: list[str] = []
    blocks: list[Block] = []
    cur = Block("text")
    lines = (md or "").replace("\r\n", "\n").split("\n")
    i = 0

    def flush():
        nonlocal cur
        if cur.paras:
            blocks.append(cur)
        cur = Block("text")
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            for c in code or [""]:
                cur.paras.append(("NORMAL_TEXT", c, [(0, u16(c), {"weightedFontFamily": {"fontFamily": MONO}})] if c else [],
                                  None, {"code": True}))
            i += 1
            continue
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 2:
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            flush()
            width = max(len(r) for r in rows) if rows else 0
            blocks.append(Block("table", rows=[r + [""] * (width - len(r)) for r in rows]))
            continue
        m = re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+)\)", s)
        if m:
            flush()
            blocks.append(Block("image", src=m.group(2), alt=m.group(1)))
            i += 1
            continue
        if s.lower() in ("---page---", "\\pagebreak", "<pagebreak>", "[page break]"):
            flush()
            blocks.append(Block("page"))
            i += 1
            continue
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", s):
            notes.append("A horizontal line has no Google Docs API change, so it was left out.")
            i += 1
            continue
        if not s:
            i += 1
            continue
        hm = re.match(r"^(#{1,6})\s+(.*)$", s)
        if hm:
            t, sp = inline(hm.group(2).strip())
            cur.paras.append((HEADINGS[len(hm.group(1))], t, sp, None, {}))
            i += 1
            continue
        tm = re.match(r"^(Title|Subtitle):\s+(.*)$", s)
        if tm:
            t, sp = inline(tm.group(2))
            cur.paras.append(("TITLE" if tm.group(1) == "Title" else "SUBTITLE", t, sp, None, {}))
            i += 1
            continue
        indent = len(ln.expandtabs(2)) - len(ln.expandtabs(2).lstrip(" "))
        level = min(8, indent // 2)
        cm = re.match(r"^[-*+]\s+\[( |x|X)\]\s+(.*)$", s)
        bm = re.match(r"^[-*+]\s+(.*)$", s)
        nm = re.match(r"^\d+[.)]\s+(.*)$", s)
        if cm:
            t, sp = inline(cm.group(2))
            cur.paras.append(("NORMAL_TEXT", t, sp, ("check", level), {"done": cm.group(1).lower() == "x"}))
        elif bm:
            t, sp = inline(bm.group(1))
            cur.paras.append(("NORMAL_TEXT", t, sp, ("bullet", level), {}))
        elif nm:
            t, sp = inline(nm.group(1))
            cur.paras.append(("NORMAL_TEXT", t, sp, ("number", level), {}))
        elif s.startswith(">"):
            t, sp = inline(s.lstrip(">").strip())
            cur.paras.append(("NORMAL_TEXT", t, sp, None, {"quote": True}))
        else:
            t, sp = inline(s)
            cur.paras.append(("NORMAL_TEXT", t, sp, None, {}))
        i += 1
    flush()
    return blocks, notes


PRESET = {"bullet": "BULLET_DISC_CIRCLE_SQUARE", "number": "NUMBERED_DECIMAL_ALPHA_ROMAN", "check": "BULLET_CHECKBOX"}


def text_requests(block: Block, index: int, mode: str, tab_id: str = "") -> tuple[list[dict], int]:
    """Requests that insert one text block at a paragraph boundary. mode 'end': in front of the tab's final newline
    ('\\n' + text); 'before': in front of a paragraph (text + '\\n'); 'empty': into an empty document (text, the
    document's own newline closes it). Returns (requests, length the block finally takes in the document)."""
    parts, offs, cur = [], [], 0
    tabs_added = 0
    for style, t, spans, bullet, extra in block.paras:
        pre = "\t" * bullet[1] if bullet else ""
        tabs_added += len(pre)
        offs.append((cur, cur + u16(pre + t), len(pre)))
        parts.append(pre + t)
        cur += u16(pre + t) + 1
    body = "\n".join(parts)
    text = {"end": "\n" + body, "before": body + "\n"}.get(mode, body)
    base = index + (1 if mode == "end" else 0)
    loc = {"index": index, **({"tabId": tab_id} if tab_id else {})}

    def rng(a, b):
        return {"startIndex": base + a, "endIndex": base + b, **({"tabId": tab_id} if tab_id else {})}
    reqs: list[dict] = [{"insertText": {"location": loc, "text": text}}]
    whole = rng(0, u16(body) + (1 if mode == "before" else 0) or 1)
    # the new text must not take over the look of the text it was put next to
    reqs.append({"updateTextStyle": {"range": rng(0, max(1, u16(body))), "textStyle": {},
                                     "fields": "bold,italic,underline,strikethrough,link,weightedFontFamily,"
                                               "foregroundColor,backgroundColor,fontSize,baselineOffset,smallCaps"}})
    reqs.append({"deleteParagraphBullets": {"range": whole}})
    for (a, b, pre), (style, t, spans, bullet, extra) in zip(offs, block.paras):
        pr = rng(a, b + 1)
        ps: dict = {"namedStyleType": style}
        fields = ["namedStyleType", "indentStart", "indentFirstLine"]     # unset = back to the style's own indent
        if extra.get("quote"):
            ps["indentStart"] = {"magnitude": 36, "unit": "PT"}
            ps["indentFirstLine"] = {"magnitude": 36, "unit": "PT"}
        reqs.append({"updateParagraphStyle": {"range": pr, "paragraphStyle": ps, "fields": ",".join(fields)}})
        for x, y, st in spans:
            if y > x:
                reqs.append({"updateTextStyle": {"range": rng(a + pre + x, a + pre + y), "textStyle": st,
                                                 "fields": ",".join(st)}})
        if extra.get("quote") and b > a:
            reqs.append({"updateTextStyle": {"range": rng(a, b), "textStyle": {"italic": True}, "fields": "italic"}})
    # lists last and from the bottom up: Google removes the leading tabs (the nesting), which moves what follows
    groups, run = [], None
    for k, (pa, pb) in enumerate(zip(block.paras, offs)):
        b = pa[3]
        if b and run and run[0] == b[0] and run[2] == k - 1:
            run[2] = k
        elif b:
            run = [b[0], k, k]
            groups.append(run)
        else:
            run = None
    for kind, k1, k2 in reversed(groups):
        reqs.append({"createParagraphBullets": {"range": rng(offs[k1][0], offs[k2][1]),
                                                "bulletPreset": PRESET[kind]}})
    return reqs, u16(text) - tabs_added


def checked(block: Block) -> list[int]:
    """Paragraph numbers (0-based inside the block) of '- [x]' items: Google's API has no field for a ticked box."""
    return [k for k, p in enumerate(block.paras) if p[3] and p[3][0] == "check" and p[4].get("done")]
