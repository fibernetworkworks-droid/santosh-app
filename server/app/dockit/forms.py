"""D5 forms: detect a PDF's fillable fields, fill them (her words, a sheet row for a batch, or masked Pehchaan Locker
references - {id:abc} is turned into the real number only here, inside the file, never shown to the model), flatten,
and CREATE a fillable form from a plain PDF (fields placed in what she sees, mm / % from the top-left).

A value that does not fit the field's choices is refused with the choices named; a field name that does not exist is
refused with the names that do. Nothing is guessed. The filled values are read back from the file before it is
called done."""
from __future__ import annotations

import io
import re
from typing import Any

from . import core, stamp
from .core import DocError

KINDS = ("text", "checkbox", "radio", "choice", "signature")
_TRUE = {"yes", "true", "1", "on", "x", "haan", "ha", "y", "checked", "tick", "✓"}


def _pypdf(data: bytes):
    import pypdf
    core.check_size(data)
    try:
        r = pypdf.PdfReader(io.BytesIO(data))
    except Exception as e:
        raise DocError(f"This PDF could not be read ({type(e).__name__}).")
    if r.is_encrypted:
        raise DocError("This PDF is locked; unlock it first (action=unlock).")
    return r


def _kind(f: dict) -> str:
    ft = str(f.get("/FT", ""))
    if ft == "/Btn":
        flags = int(f.get("/Ff", 0) or 0)
        if flags & (1 << 15):
            return "radio"
        if flags & (1 << 16):
            return "button"
        return "checkbox"
    if ft == "/Ch":
        return "choice"
    if ft == "/Sig":
        return "signature"
    return "text"


def _states(f: dict) -> list[str]:
    """The 'on' names of a checkbox / the options of a radio group."""
    out: set[str] = set()
    for w in [f] + [k.get_object() for k in (f.get("/Kids") or [])]:
        ap = w.get("/AP")
        if ap is not None:
            for k in (ap.get_object().get("/N") or {}).keys():
                if str(k) != "/Off":
                    out.add(str(k).lstrip("/"))
    return sorted(out)


def detect(data: bytes) -> list[dict[str, Any]]:
    """[{name, kind, value, options, required, read_only, page, max_len, tooltip}] in page order."""
    r = _pypdf(data)
    fields = r.get_fields() or {}
    pages: dict[str, int] = {}
    for pi, page in enumerate(r.pages):
        for a in page.get("/Annots") or []:
            a = a.get_object()
            name = a.get("/T") or (a.get("/Parent").get_object().get("/T") if a.get("/Parent") else None)
            if name is not None and str(name) not in pages:
                full = str(name)
                par = a.get("/Parent")
                while par is not None and par.get_object().get("/T") is not None and par.get_object() is not a:
                    parent = par.get_object()
                    if parent.get("/T") is None:
                        break
                    if str(parent.get("/T")) != full:
                        full = f"{parent.get('/T')}.{full}" if a.get("/T") is not None else full
                    par = parent.get("/Parent")
                pages.setdefault(str(name), pi + 1)
                pages.setdefault(full, pi + 1)
    out = []
    for name, f in fields.items():
        kind = _kind(f)
        if kind == "button":
            continue
        flags = int(f.get("/Ff", 0) or 0)
        opts = []
        if kind == "choice":
            for o in f.get("/Opt") or []:
                o = o.get_object() if hasattr(o, "get_object") else o
                opts.append(str(o[1] if isinstance(o, list) and len(o) > 1 else o))
        elif kind in ("checkbox", "radio"):
            opts = _states(f)
        v = f.get("/V")
        out.append({"name": name, "kind": kind, "value": str(v).lstrip("/") if v is not None else "",
                    "options": opts, "required": bool(flags & 2), "read_only": bool(flags & 1),
                    "page": pages.get(name.split(".")[-1]) or pages.get(name), "max_len": f.get("/MaxLen"),
                    "tooltip": str(f.get("/TU", ""))[:120]})
    return out


def _value_for(field: dict, raw: Any) -> Any:
    kind = field["kind"]
    s = str(raw if raw is not None else "").strip()
    if kind == "checkbox":
        on = s.lower() in _TRUE
        state = field["options"][0] if field["options"] else "Yes"
        return "/" + state if on else "/Off"
    if kind == "radio":
        for o in field["options"]:
            if o.lower() == s.lower():
                return "/" + o
        raise DocError(f"'{field['name']}' takes one of: {', '.join(field['options']) or '(no options)'}; not '{s}'.")
    if kind == "choice":
        if field["options"] and s not in field["options"]:
            hit = [o for o in field["options"] if o.lower() == s.lower()]
            if not hit:
                raise DocError(f"'{field['name']}' takes one of: {', '.join(field['options'][:20])}; not '{s}'.")
            s = hit[0]
        return s
    if kind == "signature":
        raise DocError(f"'{field['name']}' is a signature box: sign it with action=sign, it cannot be typed.")
    if field.get("max_len") and len(s) > int(field["max_len"]):
        raise DocError(f"'{field['name']}' holds at most {field['max_len']} characters; '{s[:20]}...' is longer.")
    return s


def fill(data: bytes, values: dict[str, Any], tenant: str = "", flatten: bool = False) -> dict[str, Any]:
    """values {field name: value}; {id:abc} references are opened from her Pehchaan Locker for this file only."""
    import logging
    from pypdf import PdfWriter
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    from pypdf.generic import NameObject
    if not values:
        raise DocError("Give the values: {field name: value} (action=form_fields lists the names).")
    fields = {f["name"]: f for f in detect(data)}
    if not fields:
        raise DocError("This PDF has no fillable fields. To make it fillable use action=form_create; to just write on "
                       "it use action=add (type text).")
    unknown = [k for k in values if k not in fields]
    if unknown:
        near = [n for n in fields if any(w in n.lower() for w in re.findall(r"\w+", unknown[0].lower()))][:6]
        raise DocError(f"No field named {', '.join(map(repr, unknown[:5]))}. " +
                       (f"Did you mean: {', '.join(near)}? " if near else "") +
                       f"Fields: {', '.join(list(fields)[:25])}.")
    locked = [k for k in values if fields[k]["read_only"]]
    if locked:
        raise DocError(f"{', '.join(locked)} {'is' if len(locked) == 1 else 'are'} read-only in this form.")
    kinds_used: list[str] = []
    real: dict[str, Any] = {}
    for k, v in values.items():
        sv = str(v if v is not None else "")
        if "{id:" in sv:
            if not tenant:
                raise DocError("A Pehchaan Locker reference needs her account.")
            from .. import idvault
            try:
                sv, kinds = idvault.fill_value(sv, tenant)
            except Exception as e:
                raise DocError(str(e))
            kinds_used += kinds
        real[k] = _value_for(fields[k], sv)
    w = PdfWriter(clone_from=io.BytesIO(data))
    text_vals = {k: v for k, v in real.items() if not str(v).startswith("/")}
    btn_vals = {k: v for k, v in real.items() if str(v).startswith("/")}
    for page in w.pages:
        if text_vals:
            try:
                w.update_page_form_field_values(page, text_vals, auto_regenerate=False)
            except Exception:
                pass
        for a in page.get("/Annots") or []:
            a = a.get_object()
            name = a.get("/T")
            par = a.get("/Parent").get_object() if a.get("/Parent") else None
            key = str(name) if name is not None else (str(par.get("/T")) if par is not None else None)
            if key is None:
                continue
            full = key if key in btn_vals else (f"{par.get('/T')}.{key}" if par is not None and par.get("/T") is not None
                                                else key)
            want = btn_vals.get(full) or btn_vals.get(key)
            if want is None:
                continue
            states = [str(s) for s in ((a.get("/AP") or {}).get("/N") or {}).keys()]
            on = want if want in states else "/Off"
            a[NameObject("/AS")] = NameObject(on)
            target = par if (par is not None and name is None) else a
            if fields.get(full, fields.get(key, {})).get("kind") == "radio" and par is not None:
                if on != "/Off":
                    par[NameObject("/V")] = NameObject(on)
            else:
                target[NameObject("/V")] = NameObject(on)
    w.set_need_appearances_writer(True)
    buf = io.BytesIO()
    w.write(buf)
    out = buf.getvalue()
    if flatten:
        from . import edit
        out, _ = edit.flatten(out)
    _readback(out, real, flatten)
    shown = {k: ("(from the locker, masked)" if "{id:" in str(values[k]) else str(v).lstrip("/")) for k, v in real.items()}
    return {"bytes": out, "filled": shown, "locker": sorted(set(kinds_used)), "flattened": bool(flatten)}


def _readback(data: bytes, want: dict[str, Any], flattened: bool) -> None:
    if flattened:
        from . import convert
        text = " ".join(convert.page_texts(data))
        missing = [k for k, v in want.items() if not str(v).startswith("/") and str(v) and str(v) not in text]
        if missing:
            raise DocError(f"Check failed: {', '.join(missing[:3])} did not land on the page; nothing was delivered.")
        return
    got = {f["name"]: f["value"] for f in detect(data)}
    bad = [k for k, v in want.items() if str(got.get(k, "")).lstrip("/") != str(v).lstrip("/")]
    if bad:
        raise DocError(f"Check failed: {', '.join(bad[:3])} did not read back as filled; nothing was delivered.")


def fill_rows(data: bytes, rows: list[dict[str, Any]], name_from: str = "", tenant: str = "",
              flatten: bool = True) -> list[dict[str, Any]]:
    """One filled copy per row (a sheet of 500 students / customers). A row that fails is reported, not dropped."""
    if not rows:
        raise DocError("The sheet has no rows.")
    if len(rows) > 500:
        raise DocError("At most 500 rows in one batch; split the sheet.")
    fields = {f["name"] for f in detect(data)}
    cols = set().union(*[set(r) for r in rows])
    use = [c for c in cols if c in fields]
    if not use:
        raise DocError(f"None of the sheet's columns match a field. Columns: {', '.join(sorted(cols)[:15])}. "
                       f"Fields: {', '.join(sorted(fields)[:15])}. Rename the columns to the field names.")
    out = []
    for i, row in enumerate(rows, 1):
        vals = {k: row[k] for k in use if row.get(k) not in (None, "")}
        label = str(row.get(name_from) or f"row {i}") if name_from else f"row {i}"
        try:
            r = fill(data, vals, tenant, flatten)
            out.append({"label": label, "bytes": r["bytes"], "ok": True})
        except DocError as e:
            out.append({"label": label, "ok": False, "error": str(e)})
    return out


def read_rows(name: str, data: bytes) -> list[dict[str, Any]]:
    """A CSV or Excel sheet -> rows (first row = column names)."""
    low = (name or "").lower()
    if low.endswith(".csv") or low.endswith(".txt"):
        import csv
        text = data.decode("utf-8-sig", errors="replace")
        return [dict(r) for r in csv.DictReader(io.StringIO(text))]
    if low.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        ws = load_workbook(io.BytesIO(data), read_only=True, data_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        head = [str(h).strip() if h is not None else "" for h in next(it, [])]
        rows = []
        for r in it:
            if r and any(v not in (None, "") for v in r):
                rows.append({head[i]: ("" if v is None else v) for i, v in enumerate(r) if i < len(head) and head[i]})
        return rows
    raise DocError("The rows must be a CSV or Excel (.xlsx) file.")


# ------------------------------------------------------------------------------------------------- create
def create(data: bytes, specs: list[dict[str, Any]]) -> tuple[bytes, list[str]]:
    """specs [{name, type text|checkbox|radio|choice|signature, page, x, y, w, h (mm or % from the top-left),
    options (choice / radio), value, required, max_len, tooltip}] -> the same PDF with real fillable fields."""
    import pikepdf
    from reportlab.pdfgen import canvas
    from .edit import _len, from_visual
    if not specs:
        raise DocError("Give the fields to add: fields=[{name, type, page, x, y, w, h}].")
    if len(specs) > 200:
        raise DocError("At most 200 fields at once.")
    names = [str(s.get("name") or "").strip() for s in specs]
    if any(not re.fullmatch(r"[A-Za-z][\w .-]{0,60}", n) for n in names):
        raise DocError("Every field needs a name of letters / numbers (e.g. 'Full name', 'agree').")
    groups = [n for n, s in zip(names, specs) if str(s.get("type")) != "radio"]
    if len(set(groups)) != len(groups):
        raise DocError("Two fields have the same name; names must be different (radio buttons share one).")
    with core.open_pdf(data) as pdf:
        existing = {str(f.get("/T")) for f in pdf.Root.get("/AcroForm", {}).get("/Fields", [])} if "/AcroForm" in pdf.Root else set()
        clash = [n for n in names if n in existing]
        if clash:
            raise DocError(f"These fields already exist: {', '.join(clash)}.")
        n = len(pdf.pages)
        by_page: dict[int, list[dict]] = {}
        for s in specs:
            kind = str(s.get("type") or "text")
            if kind not in KINDS:
                raise DocError(f"type = {' | '.join(KINDS)}.")
            p = int(s.get("page") or 1)
            if not 1 <= p <= n:
                raise DocError(f"Field '{s.get('name')}' is on page {p}; the file has {n} pages.")
            by_page.setdefault(p - 1, []).append(s)
        made: list[str] = []
        keep = []
        all_fields = pikepdf.Array(pdf.Root.AcroForm.Fields) if "/AcroForm" in pdf.Root and "/Fields" in pdf.Root.AcroForm else pikepdf.Array()
        for pi, items in by_page.items():
            page = pdf.pages[pi]
            f = stamp.frame(page)
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(f["mw"], f["mh"]))
            form = c.acroForm
            for s in items:
                kind = str(s.get("type") or "text")
                X = _len(s.get("x"), f["vw"], 20 * stamp.MM)
                top = _len(s.get("y"), f["vh"], 20 * stamp.MM)
                w = _len(s.get("w"), f["vw"], 60 * stamp.MM if kind not in ("checkbox", "radio") else 5 * stamp.MM)
                h = _len(s.get("h"), f["vh"], 8 * stamp.MM if kind != "signature" else 18 * stamp.MM)
                if kind in ("checkbox", "radio"):
                    w = h = min(w, h) if s.get("w") or s.get("h") else 5 * stamp.MM
                p1 = from_visual(f, X, f["vh"] - top - h)
                p2 = from_visual(f, X + w, f["vh"] - top)
                x0, y0 = min(p1[0], p2[0]) - f["mx"], min(p1[1], p2[1]) - f["my"]
                ww, hh = abs(p2[0] - p1[0]), abs(p2[1] - p1[1])
                nm = str(s["name"]).strip()
                tip = str(s.get("tooltip") or nm)[:100]
                common = dict(x=x0, y=y0, borderWidth=0.8, borderColor=None, fillColor=None, forceBorder=True,
                              tooltip=tip)
                if kind == "text":
                    fl = "required" if s.get("required") else ""
                    form.textfield(name=nm, width=ww, height=hh, value=str(s.get("value") or ""),
                                   maxlen=int(s.get("max_len") or 0) or None, fieldFlags=fl, fontSize=0, **common)
                elif kind == "checkbox":
                    form.checkbox(name=nm, size=ww, checked=bool(s.get("value")), **common)
                elif kind == "radio":
                    opt = str(s.get("value") or s.get("option") or "yes")
                    form.radio(name=nm, value=re.sub(r"\W", "_", opt), size=ww, selected=bool(s.get("selected")), **common)
                elif kind == "choice":
                    opts = [str(o) for o in (s.get("options") or [])]
                    if not opts:
                        raise DocError(f"Choice field '{nm}' needs options.")
                    form.choice(name=nm, options=opts, value=str(s.get("value") or opts[0]), width=ww, height=hh,
                                **common)
                else:                                              # signature: a box she or her signer signs
                    c.setStrokeColorRGB(0.4, 0.4, 0.5)
                    c.setDash(3, 2)
                    c.rect(x0, y0, ww, hh)
                    c.setDash()
                made.append(f"{nm} ({kind}, page {pi + 1})")
            c.showPage()
            c.save()
            src = pikepdf.open(io.BytesIO(buf.getvalue()))
            keep.append(src)
            sp = src.pages[0]
            annots = sp.obj.get("/Annots") or pikepdf.Array()
            dx, dy = f["mx"], f["my"]
            if "/Annots" not in page.obj:
                page.obj.Annots = pikepdf.Array()
            for a in annots:
                a2 = pdf.copy_foreign(a)
                if dx or dy:
                    r = [float(v) for v in a2.Rect]
                    a2.Rect = pikepdf.Array([r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy])
                a2.P = page.obj
                page.obj.Annots.append(a2)
                top_field = a2.get("/Parent") if a2.get("/Parent") is not None else a2
                if not any(top_field.objgen == x.objgen for x in all_fields):
                    all_fields.append(top_field)
            sigs = [s for s in items if str(s.get("type")) == "signature"]
            for s in sigs:                                   # signature fields: an empty /Sig widget
                X = _len(s.get("x"), f["vw"], 20 * stamp.MM)
                top = _len(s.get("y"), f["vh"], 20 * stamp.MM)
                w = _len(s.get("w"), f["vw"], 60 * stamp.MM)
                h = _len(s.get("h"), f["vh"], 18 * stamp.MM)
                p1, p2 = from_visual(f, X, f["vh"] - top - h), from_visual(f, X + w, f["vh"] - top)
                sig = pdf.make_indirect(pikepdf.Dictionary(
                    Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Widget, FT=pikepdf.Name.Sig,
                    T=pikepdf.String(str(s["name"]).strip()), F=4, P=page.obj,
                    Rect=pikepdf.Array([min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])])))
                page.obj.Annots.append(sig)
                all_fields.append(sig)
        if "/AcroForm" not in pdf.Root:
            pdf.Root.AcroForm = pdf.make_indirect(pikepdf.Dictionary())
        pdf.Root.AcroForm.Fields = all_fields
        pdf.Root.AcroForm.NeedAppearances = True
        if any(str(s.get("type")) == "signature" for s in specs):
            pdf.Root.AcroForm.SigFlags = 1
        try:
            src0 = keep[0] if keep else None
            dr = src0.Root.AcroForm.get("/DR") if src0 is not None and "/AcroForm" in src0.Root else None
            if dr is not None and "/DR" not in pdf.Root.AcroForm:
                pdf.Root.AcroForm.DR = pdf.copy_foreign(dr)
            da = src0.Root.AcroForm.get("/DA") if src0 is not None and "/AcroForm" in src0.Root else None
            if da is not None and "/DA" not in pdf.Root.AcroForm:
                pdf.Root.AcroForm.DA = da
        except Exception:
            pass
        out = core.save(pdf)
        for k in keep:
            k.close()
    got = {f["name"] for f in detect(out)}
    missing = [nm for nm in names if nm not in got]
    if missing:
        raise DocError(f"Check failed: fields {', '.join(missing[:4])} did not read back; nothing was delivered.")
    return out, made
