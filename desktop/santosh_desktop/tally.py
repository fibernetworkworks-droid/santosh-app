"""TallyPrime over its local XML port (Help > Settings > Connectivity: "TallyPrime acts as Server", port 9000).

Reads use Export requests. The only write is a simple two-ledger voucher, sent only after the user approved it on the phone.
Amount signs in Tally XML: debit is negative, credit is positive.
"""
from __future__ import annotations

import datetime as dt
import re
import xml.etree.ElementTree as ET
from typing import Any
from xml.sax.saxutils import escape

import httpx


class TallyError(Exception):
    pass


_BAD = re.compile(r"&#(?:[0-8]|1[0-9]|2[0-9]|3[01]);|[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _clean(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        txt = raw.decode("utf-16", "ignore")
    else:
        txt = raw.decode("utf-8", "ignore")
    return _BAD.sub("", txt)


def _num(v: str | None) -> float:
    if not v:
        return 0.0
    m = re.search(r"-?[\d,]+(?:\.\d+)?", v.replace(" ", ""))
    return float(m.group(0).replace(",", "")) if m else 0.0


def _date(v: str | None) -> str:
    v = (v or "").strip()
    if re.fullmatch(r"\d{8}", v):
        return f"{v[:4]}-{v[4:6]}-{v[6:]}"
    return v


def _tdate(v: str) -> str:
    v = (v or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v.replace("-", "")
    if re.fullmatch(r"\d{8}", v):
        return v
    raise TallyError(f"Date must be YYYY-MM-DD, got '{v}'")


def fy_start(today: dt.date | None = None) -> dt.date:
    t = today or dt.date.today()
    return dt.date(t.year if t.month >= 4 else t.year - 1, 4, 1)


def rupees(x: float) -> str:
    neg = x < 0
    x = abs(round(x, 2))
    whole, frac = divmod(round(x * 100), 100)
    s = str(int(whole))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = head + "," + tail
    out = "₹" + s + (f".{int(frac):02d}" if frac else "")
    return "-" + out if neg else out


class Tally:
    def __init__(self, host: str = "localhost", port: int = 9000, client: httpx.Client | None = None):
        self.url = f"http://{host}:{port}"
        self.client = client or httpx.Client(timeout=45)

    # ---------------- transport ----------------
    def _post(self, xml: str) -> ET.Element:
        try:
            r = self.client.post(self.url, content=xml.encode("utf-8"), headers={"Content-Type": "text/xml; charset=utf-8"})
        except httpx.HTTPError:
            raise TallyError("TallyPrime is not reachable on this PC. Open TallyPrime and turn on "
                             "Help > Settings > Connectivity > 'TallyPrime acts as Server' (port 9000).")
        txt = _clean(r.content)
        try:
            return ET.fromstring(txt)
        except ET.ParseError:
            raise TallyError("TallyPrime sent an answer Santosh could not read.")

    def _collection(self, ctype: str, fetch: str, company: str = "", sv: dict[str, str] | None = None,
                    compute: list[str] | None = None) -> list[ET.Element]:
        statics = "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
        if company:
            statics += f"<SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY>"
        for k, v in (sv or {}).items():
            statics += f"<{k}>{escape(v)}</{k}>"
        comp = "".join(f"<COMPUTE>{escape(c)}</COMPUTE>" for c in (compute or []))
        xml = (f"<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE>"
               f"<ID>SantoshColl</ID></HEADER><BODY><DESC><STATICVARIABLES>{statics}</STATICVARIABLES><TDL><TDLMESSAGE>"
               f"<COLLECTION NAME=\"SantoshColl\" ISMODIFY=\"No\"><TYPE>{ctype}</TYPE><FETCH>{fetch}</FETCH>{comp}"
               f"</COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>")
        root = self._post(xml)
        tag = ctype.upper()
        return [e for e in root.iter() if e.tag == tag]

    @staticmethod
    def _t(e: ET.Element, name: str) -> str:
        c = e.find(name)
        if c is not None and (c.text or "").strip():
            return c.text.strip()
        if name == "NAME":
            return (e.get("NAME") or "").strip()
        return ""

    # ---------------- reads ----------------
    def status(self) -> dict[str, Any]:
        try:
            comps = self.companies()
            return {"available": True, "companies": comps}
        except TallyError as e:
            return {"available": False, "reason": str(e)}

    def companies(self) -> list[str]:
        return [n for n in (self._t(e, "NAME") for e in self._collection("Company", "NAME")) if n]

    def ledgers(self, company: str = "") -> list[dict[str, Any]]:
        out = []
        for e in self._collection("Ledger", "NAME,PARENT,CLOSINGBALANCE", company,
                                  compute=["SantoshPrimary:$_PrimaryGroup"]):
            bal = _num(self._t(e, "CLOSINGBALANCE"))
            out.append({"name": self._t(e, "NAME"), "group": self._t(e, "PARENT"),
                        "primary_group": self._t(e, "SANTOSHPRIMARY") or self._t(e, "PARENT"),
                        "closing": bal, "dr_cr": "Dr" if bal < 0 else ("Cr" if bal > 0 else "")})
        return out

    def outstanding(self, which: str, company: str = "") -> dict[str, Any]:
        group = "Sundry Debtors" if which == "receivables" else "Sundry Creditors"
        rows = []
        for l in self.ledgers(company):
            if group.lower() not in (l["primary_group"] + " " + l["group"]).lower():
                continue
            amt = -l["closing"] if which == "receivables" else l["closing"]
            if round(amt, 2) > 0:
                rows.append({"party": l["name"], "amount": round(amt, 2), "amount_text": rupees(amt)})
        rows.sort(key=lambda r: -r["amount"])
        total = sum(r["amount"] for r in rows)
        return {"report": which, "group": group, "parties": rows[:100], "count": len(rows), "total": round(total, 2),
                "total_text": rupees(total)}

    def vouchers(self, from_date: str = "", to_date: str = "", company: str = "", kind: str = "",
                 party: str = "") -> dict[str, Any]:
        today = dt.date.today()
        f = _tdate(from_date) if from_date else fy_start(today).strftime("%Y%m%d")
        t = _tdate(to_date) if to_date else today.strftime("%Y%m%d")
        elems = self._collection("Voucher", "DATE,VOUCHERTYPENAME,VOUCHERNUMBER,PARTYLEDGERNAME,AMOUNT,NARRATION", company,
                                 sv={"SVFROMDATE": f, "SVTODATE": t},
                                 compute=["SantoshSales:$$IsSales:$VoucherTypeName", "SantoshPurc:$$IsPurchase:$VoucherTypeName",
                                          "SantoshRcpt:$$IsReceipt:$VoucherTypeName", "SantoshPymt:$$IsPayment:$VoucherTypeName"])
        flag = {"sales": "SANTOSHSALES", "purchases": "SANTOSHPURC", "receipts": "SANTOSHRCPT", "payments": "SANTOSHPYMT"}.get(kind)
        word = {"sales": "sales", "purchases": "purchase", "receipts": "receipt", "payments": "payment"}.get(kind, "")
        rows = []
        for e in elems:
            vt = self._t(e, "VOUCHERTYPENAME")
            if flag:
                fl = self._t(e, flag).lower()
                if fl not in ("yes", "true", "1") and word not in vt.lower():
                    continue
            p = self._t(e, "PARTYLEDGERNAME")
            if party and party.lower() not in p.lower():
                continue
            d = _date(self._t(e, "DATE"))
            if not (f <= d.replace("-", "") <= t):
                continue
            amt = abs(_num(self._t(e, "AMOUNT")))
            rows.append({"date": d, "type": vt, "number": self._t(e, "VOUCHERNUMBER"), "party": p, "amount": round(amt, 2),
                         "amount_text": rupees(amt), "narration": self._t(e, "NARRATION")[:120]})
        rows.sort(key=lambda r: (r["date"], r["number"]))
        total = sum(r["amount"] for r in rows)
        return {"report": kind or "vouchers", "from": _date(f), "to": _date(t), "vouchers": rows[-200:], "count": len(rows),
                "total": round(total, 2), "total_text": rupees(total)}

    def stock(self, company: str = "") -> dict[str, Any]:
        rows = []
        for e in self._collection("StockItem", "NAME,PARENT,BASEUNITS,CLOSINGBALANCE,CLOSINGVALUE", company):
            val = abs(_num(self._t(e, "CLOSINGVALUE")))
            rows.append({"item": self._t(e, "NAME"), "group": self._t(e, "PARENT"), "quantity": self._t(e, "CLOSINGBALANCE"),
                         "value": round(val, 2), "value_text": rupees(val)})
        rows.sort(key=lambda r: -r["value"])
        return {"report": "stock", "items": rows[:300], "count": len(rows),
                "total_value_text": rupees(sum(r["value"] for r in rows))}

    def report(self, report: str, from_date: str = "", to_date: str = "", party: str = "", company: str = "") -> dict[str, Any]:
        report = (report or "").lower()
        if report == "companies":
            return {"report": "companies", "companies": self.companies()}
        if report == "ledgers":
            ls = self.ledgers(company)
            return {"report": "ledgers", "count": len(ls), "ledgers": [{**l, "closing_text": rupees(abs(l["closing"]))} for l in ls[:400]]}
        if report in ("receivables", "payables"):
            return self.outstanding(report, company)
        if report in ("sales", "purchases", "receipts", "payments"):
            return self.vouchers(from_date, to_date, company, report)
        if report == "daybook":
            d = from_date or dt.date.today().isoformat()
            return {**self.vouchers(d, to_date or d, company), "report": "daybook"}
        if report == "stock":
            return self.stock(company)
        if report == "ledger":
            if not party:
                raise TallyError("Which party? Give the ledger name.")
            match = [l for l in self.ledgers(company) if party.lower() in l["name"].lower()]
            if not match:
                raise TallyError(f"No ledger like '{party}' in Tally.")
            led = match[0]
            v = self.vouchers(from_date, to_date, company, "", led["name"])
            return {"report": "ledger", "ledger": led["name"], "group": led["group"],
                    "closing": rupees(abs(led["closing"])) + (" " + led["dr_cr"] if led["dr_cr"] else ""), **{k: v[k] for k in ("from", "to", "vouchers", "count")}}
        raise TallyError(f"Unknown Tally report '{report}'")

    # ---------------- the one write ----------------
    def create_voucher(self, voucher_type: str, party: str, amount: float, ledger: str, date: str = "",
                       narration: str = "", company: str = "") -> dict[str, Any]:
        names = {l["name"].lower(): l["name"] for l in self.ledgers(company)}
        if party.lower() not in names:
            raise TallyError(f"Ledger '{party}' is not in Tally. Use the exact ledger name.")
        if ledger.lower() not in names:
            raise TallyError(f"Ledger '{ledger}' is not in Tally. Use the exact ledger name.")
        party, ledger = names[party.lower()], names[ledger.lower()]
        amt = round(float(amount), 2)
        # (debit ledger, credit ledger)
        dr, cr = {"Sales": (party, ledger), "Purchase": (ledger, party), "Receipt": (ledger, party),
                  "Payment": (party, ledger)}[voucher_type]
        d = _tdate(date) if date else dt.date.today().strftime("%Y%m%d")
        comp = f"<STATICVARIABLES><SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY></STATICVARIABLES>" if company else ""

        def line(name: str, debit: bool) -> str:
            return (f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{escape(name)}</LEDGERNAME>"
                    f"<ISDEEMEDPOSITIVE>{'Yes' if debit else 'No'}</ISDEEMEDPOSITIVE>"
                    f"<AMOUNT>{-amt if debit else amt:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")
        xml = (f"<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC>"
               f"<REPORTNAME>Vouchers</REPORTNAME>{comp}</REQUESTDESC><REQUESTDATA><TALLYMESSAGE xmlns:UDF=\"TallyUDF\">"
               f"<VOUCHER VCHTYPE=\"{voucher_type}\" ACTION=\"Create\"><DATE>{d}</DATE>"
               f"<VOUCHERTYPENAME>{voucher_type}</VOUCHERTYPENAME><PARTYLEDGERNAME>{escape(party)}</PARTYLEDGERNAME>"
               f"<NARRATION>{escape(narration or 'Entered by Santosh after approval')}</NARRATION>"
               f"{line(dr, True)}{line(cr, False)}</VOUCHER></TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")
        root = self._post(xml)
        created = int(_num((root.findtext(".//CREATED") or "0")))
        errors = [e.text.strip() for e in root.iter("LINEERROR") if e.text and e.text.strip()]
        if created < 1:
            raise TallyError("Tally did not save the entry" + (": " + "; ".join(errors[:3]) if errors else "."))
        return {"created": created, "voucher_type": voucher_type, "party": party, "ledger": ledger, "amount": amt,
                "amount_text": rupees(amt), "date": _date(d), "message": f"Tally mein {voucher_type} entry ho gayi: {party} {rupees(amt)}."}
