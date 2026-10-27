"""Reading and building emails (RFC 822 / MIME), the same for every provider.

Gmail (raw), Outlook (/$value) and IMAP (RFC822) all hand us the full MIME message, so parsing, attachments and
building replies live here once.
"""
from __future__ import annotations

import email
import email.utils
import html as _html
import io
import mimetypes
import re
import zipfile
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from typing import Any

BODY_LIMIT = 12000
NOREPLY = re.compile(r"(no[-_.]?reply|donotreply|do-not-reply|mailer-daemon|notifications?@|alerts?@|newsletter|bounce)", re.I)


def dec(raw) -> str:
    if raw is None:
        return ""
    try:
        return str(make_header(decode_header(str(raw)))).strip()
    except Exception:
        return str(raw).strip()


def addr(raw) -> tuple[str, str]:
    name, a = email.utils.parseaddr(dec(raw))
    return (name or a, a.lower())


def addr_list(raw) -> list[tuple[str, str]]:
    out = []
    for name, a in email.utils.getaddresses([dec(raw)] if raw else []):
        if a and "@" in a:
            out.append((name or a, a.lower()))
    return out


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|head).*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|tr|li|h[1-6]|table)>", "\n", html)
    text = re.sub(r"<[^>]+>", " ", html)
    text = _html.unescape(text)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _payload(part: Message) -> str:
    try:
        data = part.get_payload(decode=True)
        if data is None:
            return ""
        return data.decode(part.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return ""


def _is_attachment(part: Message) -> bool:
    if part.is_multipart():
        return False
    disp = str(part.get("Content-Disposition") or "").lower()
    if disp.startswith("attachment"):
        return True
    fname = part.get_filename()
    ctype = part.get_content_type()
    if fname and ctype not in ("text/plain", "text/html"):
        return True
    return disp.startswith("inline") and bool(fname) and not ctype.startswith("text/")


def _parts(msg: Message) -> list[Message]:
    return [p for p in msg.walk() if not p.is_multipart()]


def body_text(msg: Message) -> str:
    plain = html_part = None
    for p in _parts(msg):
        if _is_attachment(p):
            continue
        ct = p.get_content_type()
        if ct == "text/plain" and plain is None:
            plain = p
        elif ct == "text/html" and html_part is None:
            html_part = p
    if plain is not None:
        t = _payload(plain).strip()
        if t:
            return t
    if html_part is not None:
        return html_to_text(_payload(html_part))
    return ""


def attachments(msg: Message) -> list[dict[str, Any]]:
    """Attachment ids are their position among the message's leaf parts: stable for the same message."""
    out = []
    for i, p in enumerate(_parts(msg)):
        if not _is_attachment(p):
            continue
        data = p.get_payload(decode=True) or b""
        name = dec(p.get_filename()) or f"attachment-{i}{mimetypes.guess_extension(p.get_content_type()) or ''}"
        out.append({"id": str(i), "name": name, "mime": p.get_content_type(), "size": len(data)})
    return out


def get_attachment(raw: bytes, att_id: str) -> tuple[str, str, bytes]:
    msg = email.message_from_bytes(raw)
    parts = _parts(msg)
    try:
        p = parts[int(att_id)]
    except (ValueError, IndexError):
        raise KeyError("attachment not found")
    if not _is_attachment(p):
        raise KeyError("attachment not found")
    return (dec(p.get_filename()) or f"attachment-{att_id}", p.get_content_type(), p.get_payload(decode=True) or b"")


def headers_of(msg: Message) -> dict[str, Any]:
    name, a = addr(msg.get("From"))
    return {
        "from": name, "from_email": a,
        "to": dec(msg.get("To")), "cc": dec(msg.get("Cc")), "reply_to": dec(msg.get("Reply-To")),
        "subject": dec(msg.get("Subject")) or "(no subject)",
        "date": dec(msg.get("Date")),
        "message_id": (msg.get("Message-ID") or "").strip(),
        "in_reply_to": (msg.get("In-Reply-To") or "").strip(),
        "references": " ".join(str(msg.get("References") or "").split()),
        "bulk": bool(msg.get("List-Unsubscribe") or str(msg.get("Precedence") or "").lower() in ("bulk", "list", "junk")
                     or str(msg.get("Auto-Submitted") or "no").lower() != "no"),
    }


def parse(raw: bytes) -> dict[str, Any]:
    msg = email.message_from_bytes(raw)
    out = headers_of(msg)
    body = body_text(msg)
    out["body"] = body[:BODY_LIMIT]
    out["truncated"] = len(body) > BODY_LIMIT
    out["attachments"] = attachments(msg)
    return out


def snippet_of(raw_partial: bytes, n: int = 220) -> str:
    """Best-effort preview from the first part of a message (IMAP partial fetch)."""
    try:
        msg = email.message_from_bytes(raw_partial)
        t = body_text(msg)
    except Exception:
        t = ""
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n]


def is_automated(sender: str, bulk: bool = False) -> bool:
    return bulk or bool(NOREPLY.search(sender or ""))


# ---------------- building ----------------
_MD_CODE = re.compile(r"`([^`\n]+)`")
_MD_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
_MD_ITAL = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)|(?<![\w])_([^_\n]+)_(?![\w])")
_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_BARE_URL = re.compile(r"(?<![\"'>=\w])(https?://[^\s<]+)")


def md_to_plain(md: str) -> str:
    """Markdown-lite -> plain text (markers stripped, links shown as text (url))."""
    text = _MD_LINK.sub(lambda m: f"{m.group(1)} ({m.group(2)})", str(md or ""))
    text = _MD_BOLD.sub(r"\1", text)
    text = _MD_ITAL.sub(lambda m: m.group(1) or m.group(2) or "", text)
    text = _MD_CODE.sub(r"\1", text)
    text = re.sub(r"^#{1,4}\s+", "", text, flags=re.M)
    return text


def md_to_html(md: str) -> str:
    """Markdown-lite -> safe HTML. EVERYTHING is html-escaped first, so the output can only contain the
    few tags we generate ourselves (b, i, code, a, p, br, ul/ol/li, h3) — no script ever survives."""
    text = _html.escape(str(md or "").replace("\r\n", "\n"))
    text = _MD_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", text)
    text = _MD_BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = _MD_ITAL.sub(lambda m: f"<i>{m.group(1) or m.group(2)}</i>", text)
    text = _MD_LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    text = _BARE_URL.sub(lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', text)
    out: list[str] = []
    list_tag = ""

    def _close_list():
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = ""

    for ln in text.split("\n"):
        s = ln.strip()
        bullet = re.match(r"[-*]\s+(.*)", s)
        number = re.match(r"\d+[.)]\s+(.*)", s)
        heading = re.match(r"#{1,4}\s+(.*)", s)
        if heading and not bullet:
            _close_list()
            out.append(f"<h3>{heading.group(1)}</h3>")
        elif bullet:
            if list_tag != "ul":
                _close_list()
                out.append("<ul>")
                list_tag = "ul"
            out.append(f"<li>{bullet.group(1)}</li>")
        elif number:
            if list_tag != "ol":
                _close_list()
                out.append("<ol>")
                list_tag = "ol"
            out.append(f"<li>{number.group(1)}</li>")
        elif s:
            _close_list()
            out.append(f"<p>{s}</p>")
        else:
            _close_list()
    _close_list()
    return "".join(out)


def build(*, from_addr: str, from_name: str, to: str, subject: str, body: str, cc: str = "", bcc: str = "",
          in_reply_to: str | None = None, references: str | None = None,
          files: list[tuple[str, str, bytes]] | None = None,
          html_body: str | None = None,
          inline: list[tuple[str, str, bytes, str]] | None = None) -> EmailMessage:
    """html_body: the rich alternative part (already safe — md_to_html output). inline: (name, mime, data, cid)
    images the html references as <img src="cid:...">; they ride inside the html part (multipart/related)."""
    msg = EmailMessage()
    msg["From"] = email.utils.formataddr((str(make_header([(from_name or from_addr.split("@")[0], "utf-8")])), from_addr))
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain=(from_addr.split("@")[-1] or "santosh.local"))
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = f"{references} {in_reply_to}".strip() if references else in_reply_to
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
        for name, mtype, data, cid in inline or []:
            sub = (mtype or "image/png").split("/", 1)[1]
            msg.get_payload()[1].add_related(data, maintype="image", subtype=sub, cid=f"<{cid}>", filename=name)
    for name, mime, data in files or []:
        maintype, _, subtype = (mime or "application/octet-stream").partition("/")
        msg.add_attachment(data, maintype=maintype or "application", subtype=subtype or "octet-stream", filename=name)
    return msg


def recipients(msg: EmailMessage) -> list[str]:
    return [a for _, a in email.utils.getaddresses([msg.get("To", ""), msg.get("Cc", ""), msg.get("Bcc", "")]) if a]


def quote(orig: dict[str, Any], limit: int = 4000) -> str:
    body = (orig.get("body") or "")[:limit]
    head = f"On {orig.get('date', '')}, {orig.get('from', '')} <{orig.get('from_email', '')}> wrote:"
    return head + "\n" + "\n".join("> " + ln for ln in body.splitlines())


def forward_block(orig: dict[str, Any], limit: int = 8000) -> str:
    return ("---------- Forwarded message ---------\n"
            f"From: {orig.get('from', '')} <{orig.get('from_email', '')}>\nDate: {orig.get('date', '')}\n"
            f"Subject: {orig.get('subject', '')}\nTo: {orig.get('to', '')}\n\n" + (orig.get("body") or "")[:limit])


# ---------------- reading attachments ----------------
TEXT_LIMIT = 15000


def attachment_text(name: str, mime: str, data: bytes, limit: int = 0, max_pages: int = 40) -> dict[str, Any]:
    """Text out of a PDF / Word / PowerPoint / Excel / CSV / text attachment, for Santosh to read."""
    TEXT_LIMIT = limit or globals()["TEXT_LIMIT"]
    low = (name or "").lower()
    try:
        if mime == "application/pdf" or low.endswith(".pdf"):
            try:
                from pypdf import PdfReader
            except ImportError:
                return {"kind": "pdf", "text": "", "note": "PDF reader (pypdf) is not installed on the server"}
            r = PdfReader(io.BytesIO(data))
            pages = [(pg.extract_text() or "") for pg in r.pages[:max_pages]]
            text = "\n\n".join(f"[page {i + 1}]\n{t.strip()}" for i, t in enumerate(pages) if t.strip())
            note = "" if text.strip() else "No text inside this PDF (it is probably a scanned image)."
            return {"kind": "pdf", "pages": len(r.pages), "text": text[:TEXT_LIMIT], "truncated": len(text) > TEXT_LIMIT, "note": note}
        if low.endswith(".docx"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml = z.read("word/document.xml").decode("utf-8", "replace")
            xml = re.sub(r"</w:p>", "\n", xml)
            text = _html.unescape(re.sub(r"<[^>]+>", "", xml)).strip()
            return {"kind": "word", "text": text[:TEXT_LIMIT], "truncated": len(text) > TEXT_LIMIT}
        if low.endswith(".pptx"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                               key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))
                parts = []
                for i, n in enumerate(names):
                    xml = z.read(n).decode("utf-8", "replace")
                    xml = re.sub(r"</a:p>", "\n", xml)
                    parts.append(f"[slide {i + 1}]\n" + _html.unescape(re.sub(r"<[^>]+>", "", xml)).strip())
            text = "\n\n".join(parts)
            return {"kind": "powerpoint", "slides": len(names), "text": text[:TEXT_LIMIT], "truncated": len(text) > TEXT_LIMIT}
        if low.endswith((".xlsx", ".xlsm")):
            rows = table_rows(name, data)
            lines = [" | ".join(str(c) for c in r) for r in rows[:300]]
            text = "\n".join(lines)
            return {"kind": "excel", "rows": len(rows), "text": text[:TEXT_LIMIT], "truncated": len(text) > TEXT_LIMIT}
        if low.endswith((".csv", ".txt", ".md", ".json", ".xml", ".log")) or mime.startswith("text/"):
            text = data.decode("utf-8", "replace")
            if mime == "text/html" or low.endswith((".html", ".htm")):
                text = html_to_text(text)
            return {"kind": "text", "text": text[:TEXT_LIMIT], "truncated": len(text) > TEXT_LIMIT}
        if mime.startswith("image/"):
            return {"kind": "image", "text": "", "note": "This is a picture. Send it to the phone (do='phone') so the user can see it."}
    except Exception as e:
        return {"kind": "unknown", "text": "", "note": f"Could not read this file ({type(e).__name__})"}
    return {"kind": "file", "text": "", "note": "Santosh can't read this file type; send it to the phone or PC instead."}


def table_rows(name: str, data: bytes) -> list[list[Any]]:
    """Rows of a CSV or Excel file (first sheet), header row first."""
    low = (name or "").lower()
    if low.endswith((".xlsx", ".xlsm")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows = [["" if c is None else c for c in r] for r in ws.iter_rows(values_only=True)]
        wb.close()
    else:
        import csv
        text = data.decode("utf-8-sig", "replace")
        try:
            dialect = csv.Sniffer().sniff(text[:4000], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = [r for r in csv.reader(io.StringIO(text), dialect)]
    while rows and not any(str(c).strip() for c in rows[-1]):
        rows.pop()
    return rows
